import contextlib
import io
import json
import unittest
from unittest.mock import patch
import pack_plan_example


class PackExampleTest(unittest.TestCase):
    def test_all_previews_are_offline_even_with_a_key(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Unexpected HTTP')), \
                patch.dict('os.environ', {'AGENT_UTILITIES_API_KEY': 'should-not-be-read'}):
            for scenario in ['unit-price-trap', 'limited-stock', 'insufficient-stock']:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    pack_plan_example.main(['--scenario', scenario])
                preview = json.loads(output.getvalue())
                self.assertEqual(preview['mode'], 'offline-preview')
                self.assertEqual(preview['scenario'], scenario)
                self.assertEqual(preview['maxPriceMicroUsd'], 800)
                self.assertNotIn('should-not-be-read', output.getvalue())

    def test_explicit_execution_uses_the_previewed_call_and_cap(self):
        output = io.StringIO()
        with patch.object(pack_plan_example, 'Client') as client, contextlib.redirect_stdout(output):
            client.return_value.execute.return_value = {'result': 'fixture'}
            pack_plan_example.main(['--scenario', 'limited-stock', '--execute'])
        client.return_value.execute.assert_called_once()
        call = client.return_value.execute.call_args.args[0]
        preview = json.loads(output.getvalue().splitlines()[0])
        self.assertEqual(call.request_id, preview['requestId'])
        self.assertEqual(json.loads(call.body), preview['input'])
        self.assertEqual(call.max_price_micro_usd, 800)
        self.assertEqual(call.tool_id, 'commerce.pack-plan')
