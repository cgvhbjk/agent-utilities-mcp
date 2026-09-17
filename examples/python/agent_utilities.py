"""Agent Utilities HTTP client. Python 3.10+, standard library only. MIT licensed.

Discovery is free. execute() spends prepaid credits, with an explicit per-call
ceiling. Keep the PreparedCall to recover uncertain outcomes without a new debit.
"""
from __future__ import annotations

import http.client
import json
import re
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any

ORIGIN = 'https://agent-utilities.agent-utilities.workers.dev'
_INPUT_LIMIT = 131072
_RESPONSE_LIMIT = 2097152


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class PreparedCall:
    tool_id: str
    request_id: str
    max_price_micro_usd: int
    body: bytes = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.tool_id, str) or not re.fullmatch(r'[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*', self.tool_id):
            raise ValueError('Invalid tool ID.')
        if not isinstance(self.request_id, str) or not re.fullmatch(r'\d{13}_[A-Za-z0-9_-]{16,80}', self.request_id):
            raise ValueError('Invalid request ID.')
        if type(self.max_price_micro_usd) is not int or not 0 <= self.max_price_micro_usd <= 999999999999:
            raise ValueError('Price ceiling must be an integer from 0 to 999999999999.')
        if not isinstance(self.body, bytes) or len(self.body) > _INPUT_LIMIT:
            raise ValueError('Input must be JSON bytes within 128 KiB.')
        try:
            value = json.loads(self.body, parse_constant=_invalid_constant)
            if not isinstance(value, dict):
                raise ValueError()
        except (ValueError, UnicodeError, RecursionError):
            raise ValueError('Input must be a JSON object with finite numbers.') from None


def _invalid_constant(_value):
    raise ValueError('Nonfinite JSON number.')


def prepare_call(tool_id: str, arguments: dict[str, Any], *, max_price_micro_usd: int,
                 request_id: str | None = None) -> PreparedCall:
    """Prepare once, offline. Reuse this object for every retry of this operation."""
    try:
        body = json.dumps(arguments, allow_nan=False, ensure_ascii=True, separators=(',', ':')).encode('utf8')
    except (TypeError, ValueError, RecursionError):
        raise ValueError('Arguments must be a JSON object with finite numbers.') from None
    return PreparedCall(tool_id, request_id if request_id is not None else f'{int(time.time() * 1000)}_{uuid.uuid4()}',
                        max_price_micro_usd, body)


class CallError(RuntimeError):
    """A safe error message plus the original prepared call for recovery.

    Never assume a rejected retry means an earlier attempt did not charge.
    """
    def __init__(self, call: PreparedCall, code: str, status: int | None = None):
        self.call, self.code, self.status = call, code, status
        super().__init__(f'{code}; request ID {call.request_id}. Preserve this PreparedCall. '
                         'Retry the same operation within ten minutes; do not generate a new ID. '
                         'An earlier attempt may already have spent credits.')


class Client:
    def __init__(self, api_key: str | None = None, *, _opener=None):
        if api_key is not None and (not isinstance(api_key, str) or not re.fullmatch(r'au_(live|test)_[a-f0-9]{64}', api_key)):
            raise ValueError('Use an API key, not a recovery credential.')
        self._api_key = api_key
        # Private injection is for fixtures. The normal client has no origin override.
        self._opener = _opener or urllib.request.build_opener(_NoRedirect())

    def _json(self, request: urllib.request.Request):
        with self._opener.open(request, timeout=15) as response:
            if response.status != 200:
                raise ValueError('Unexpected response status.')
            raw = response.read(_RESPONSE_LIMIT + 1)
            if len(raw) > _RESPONSE_LIMIT:
                raise ValueError('Response exceeds limit.')
            data = json.loads(raw, parse_constant=_invalid_constant)
            if not isinstance(data, dict):
                raise ValueError('Invalid response.')
            return data

    def _read(self, path: str):
        request = urllib.request.Request(ORIGIN + path, headers={
            'Accept': 'application/json', 'User-Agent': 'Agent-Utilities-Python/0.1.0'})
        try:
            return self._json(request)
        except urllib.error.HTTPError as error:
            error.close()
            raise RuntimeError('Public discovery unavailable. No paid request sent by this read.') from None
        except (OSError, http.client.HTTPException, ValueError, RecursionError):
            raise RuntimeError('Public discovery unavailable. No paid request sent by this read.') from None

    def catalog(self):
        """Free schemas, examples, prices and workflow/documentation links. No key sent."""
        return self._read('/v1/content')

    def status(self):
        """Free service mode and capabilities. No key sent."""
        return self._read('/billing/api/status')

    def execute(self, call: PreparedCall):
        """Spend at most the supplied ceiling for a new reservation.

        One automatic retry preserves body, ID and ceiling. Existing reservations
        are not undone by a lower cap. Returns result, receipt and recovery expiry.
        """
        if not isinstance(call, PreparedCall):
            raise TypeError('Pass a PreparedCall from prepare_call().')
        if not self._api_key:
            raise CallError(call, 'api_key_required')
        try:
            status = self.status()
        except RuntimeError:
            raise CallError(call, 'status_unavailable') from None
        if status.get('enabled') is not True or status.get('mode') != self._api_key.split('_')[1]:
            raise CallError(call, 'credit_mode_unavailable')
        if status.get('creditPriceLimits') is not True:
            raise CallError(call, 'price_limits_unavailable')
        request = urllib.request.Request(ORIGIN + '/v1/tools/' + call.tool_id, data=call.body, method='POST', headers={
            'Accept': 'application/json', 'Content-Type': 'application/json',
            'User-Agent': 'Agent-Utilities-Python/0.1.0', 'Authorization': 'Bearer ' + self._api_key,
            'Idempotency-Key': call.request_id, 'X-Max-Credit-Micro-Usd': str(call.max_price_micro_usd),
        })
        last_status = None
        for attempt in range(2):
            try:
                data = self._json(request)
                receipt = data.get('receipt')
                if (data.get('settlementStatus') != 'service-credits-debited' or 'result' not in data
                        or not isinstance(receipt, dict) or receipt.get('mode') != status['mode']
                        or not isinstance(receipt.get('chargedMicroUsd'), str)
                        or not re.fullmatch(r'\d+', receipt['chargedMicroUsd'])
                        or not isinstance(data.get('recoveryExpiresAt'), str)):
                    raise ValueError('Invalid paid response.')
                return data
            except urllib.error.HTTPError as error:
                last_status = error.code
                code = 'request_rejected'
                try:
                    raw = error.read(_RESPONSE_LIMIT + 1)
                    if len(raw) <= _RESPONSE_LIMIT:
                        candidate = json.loads(raw).get('error', {}).get('code')
                        if isinstance(candidate, str) and re.fullmatch(r'[a-z_]{1,60}', candidate):
                            code = candidate
                except (OSError, http.client.HTTPException, ValueError, AttributeError, RecursionError):
                    pass
                finally:
                    error.close()
                if 300 <= last_status < 500 and last_status != 408:
                    raise CallError(call, code, last_status) from None
            except (OSError, http.client.HTTPException, ValueError, RecursionError):
                pass  # Transport errors may contain secrets; never surface their text.
            if attempt == 0:
                time.sleep(0.25)
        raise CallError(call, 'outcome_uncertain', last_status) from None
