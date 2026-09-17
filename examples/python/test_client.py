import io
import json
import unittest
import urllib.error
from unittest.mock import patch
from agent_utilities import Client, CallError, PreparedCall, prepare_call, ORIGIN, _NoRedirect

KEY = 'au_test_' + 'a' * 64
STATUS = {'enabled': True, 'mode': 'test', 'creditPriceLimits': True}
RESPONSE = {'result': {'valid': True}, 'receipt': {'id': 'fixture', 'mode': 'test', 'chargedMicroUsd': '300'},
            'settlementStatus': 'service-credits-debited', 'recoveryExpiresAt': '2026-09-17T19:00:00Z'}

class Response(io.BytesIO):
    status = 200
    def __init__(self, data):
        super().__init__(data if isinstance(data, bytes) else json.dumps(data).encode())

class Opener:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []
    def open(self, request, timeout):
        self.requests.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return Response(reply)

class ClientTests(unittest.TestCase):
    def prepare(self, **kwargs):
        return prepare_call('commerce.gtin-validate', {'code': '036000291452'}, max_price_micro_usd=300, **kwargs)

    def test_offline_preparation_freezes_input_and_rejects_unsafe_values(self):
        original = {'code': '036000291452'}
        call = prepare_call('commerce.gtin-validate', original, max_price_micro_usd=300)
        original['code'] = 'changed'
        self.assertEqual(json.loads(call.body)['code'], '036000291452')
        self.assertNotIn('036000291452', repr(call))
        for ceiling in [True, -1, 1.2, '300', 1000000000000]:
            with self.assertRaises(ValueError):
                prepare_call('commerce.gtin-validate', {}, max_price_micro_usd=ceiling)
        for arguments in [[], {'x': float('nan')}, {'x': 'a' * 131072}]:
            with self.assertRaises(ValueError):
                prepare_call('commerce.gtin-validate', arguments, max_price_micro_usd=300)
        with self.assertRaises(ValueError):
            prepare_call('../other', {}, max_price_micro_usd=300)
        with self.assertRaises(ValueError):
            self.prepare(request_id='bad')

    def test_discovery_never_sends_key(self):
        opener = Opener([{'tools': []}, STATUS])
        client = Client(KEY, _opener=opener)
        client.catalog(); client.status()
        self.assertTrue(all(r.get_header('Authorization') is None for r in opener.requests))
        self.assertTrue(all(r.get_method() == 'GET' for r in opener.requests))

    def test_missing_key_mode_or_capability_never_sends_paid_request(self):
        for status in [{}, {**STATUS, 'mode': 'live'}, {**STATUS, 'creditPriceLimits': False}]:
            opener = Opener([status])
            with self.assertRaises(CallError):
                Client(KEY, _opener=opener).execute(self.prepare())
            self.assertEqual(len(opener.requests), 1)
        opener = Opener([])
        with self.assertRaises(CallError):
            Client(_opener=opener).execute(self.prepare())
        self.assertEqual(opener.requests, [])
        with self.assertRaises(ValueError):
            Client('au_recovery_test_' + 'a' * 64)

    @patch('agent_utilities.time.sleep')
    def test_lost_response_retries_identical_body_identity_and_cap(self, _sleep):
        opener = Opener([STATUS, OSError('secret ' + KEY), RESPONSE])
        call = self.prepare()
        self.assertEqual(Client(KEY, _opener=opener).execute(call), RESPONSE)
        first, second = opener.requests[1:]
        self.assertIs(first, second)
        self.assertEqual(first.data, call.body)
        self.assertEqual(first.get_header('Idempotency-key'), call.request_id)
        self.assertEqual(first.get_header('X-max-credit-micro-usd'), '300')
        self.assertEqual(first.full_url, ORIGIN + '/v1/tools/commerce.gtin-validate')

    def test_price_rejection_does_not_retry_or_raise_the_ceiling(self):
        error = urllib.error.HTTPError(ORIGIN, 412, 'bad ' + KEY, {}, io.BytesIO(b'{"error":{"code":"price_limit_exceeded"}}'))
        opener = Opener([STATUS, error])
        call = self.prepare()
        with self.assertRaises(CallError) as caught:
            Client(KEY, _opener=opener).execute(call)
        self.assertIs(caught.exception.call, call)
        self.assertEqual(caught.exception.code, 'price_limit_exceeded')
        self.assertNotIn(KEY, str(caught.exception))
        self.assertEqual(len(opener.requests), 2)

    @patch('agent_utilities.time.sleep')
    def test_uncertain_response_retains_recovery_and_redacts_transport_details(self, _sleep):
        opener = Opener([STATUS, b'not-json', OSError('secret ' + KEY)])
        call = self.prepare()
        with self.assertRaises(CallError) as caught:
            Client(KEY, _opener=opener).execute(call)
        self.assertIs(caught.exception.call, call)
        self.assertEqual(caught.exception.code, 'outcome_uncertain')
        self.assertNotIn(KEY, str(caught.exception))
        self.assertNotIn('036000291452', str(caught.exception))

    def test_redirects_cannot_forward_authorization(self):
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 307, '', {}, 'https://other.test'))
        opener = Opener([STATUS, urllib.error.HTTPError(ORIGIN, 307, 'redirect', {}, io.BytesIO(b''))])
        with self.assertRaises(CallError):
            Client(KEY, _opener=opener).execute(self.prepare())
        self.assertEqual(len(opener.requests), 2)

    @patch('agent_utilities.time.sleep')
    def test_response_limit_is_bounded(self, _sleep):
        opener = Opener([STATUS, b' ' * 2097153, b' ' * 2097153])
        with self.assertRaises(CallError) as caught:
            Client(KEY, _opener=opener).execute(self.prepare())
        self.assertEqual(caught.exception.code, 'outcome_uncertain')

if __name__ == '__main__':
    unittest.main()
