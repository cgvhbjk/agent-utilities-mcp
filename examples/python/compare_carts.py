"""Compare supplied checkout snapshots. Preview is offline; --execute spends credits."""
import argparse
import json
import os
import re
from pathlib import Path
from agent_utilities import Client, CallError, prepare_call

CALL_CEILING = 500
_COSTS = ('shipping', 'tax', 'fees')


def _object(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() <= set(required) | set(optional):
        raise ValueError('Input fields must match cart_comparison_example.json.')


def _id(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 100:
        raise ValueError('Each cart and item needs an ID of 1–100 characters.')
    return value


def _units(value, digits, *, result=False):
    # Python integers avoid binary floats and Decimal context rounding.
    pattern = r'(0|[1-9][0-9]*)(\.[0-9]{1,6})?' if result else r'(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?'
    if not isinstance(value, str) or len(value) > (32 if result else 19) or not re.fullmatch(pattern, value):
        raise ValueError('Amounts must be nonnegative decimal strings.')
    whole, _, part = value.partition('.')
    if len(part) > digits:
        raise ValueError('Amount precision exceeds minorUnitDigits; no implicit rounding.')
    return int(whole) * 10 ** digits + int(part.ljust(digits, '0') or '0')


def prepare_comparison(value, *, max_total_micro_usd=1000):
    """Validate all candidates and budget before preparing any paid operation."""
    _object(value, ('currency', 'minorUnitDigits', 'carts'))
    if not isinstance(value['currency'], str) or not re.fullmatch(r'[A-Z]{3}', value['currency']):
        raise ValueError('Declare one three-letter currency for all carts; no conversion.')
    digits = value['minorUnitDigits']
    if type(digits) is not int or not 0 <= digits <= 6:
        raise ValueError('minorUnitDigits must be an integer from 0 to 6.')
    carts = value['carts']
    if not isinstance(carts, list) or not 2 <= len(carts) <= 10:
        raise ValueError('Supply 2–10 comparable checkout snapshots.')
    if type(max_total_micro_usd) is not int or not 0 <= max_total_micro_usd <= 5000:
        raise ValueError('Total ceiling must be an integer from 0 to 5000 micro-dollars.')
    if len(carts) * CALL_CEILING > max_total_micro_usd:
        raise ValueError('Candidate count exceeds the total budget at 500 micro-dollars per call.')
    ids, inputs = set(), []
    for cart in carts:
        _object(cart, ('id', 'items', 'orderDiscount', *_COSTS), ('declaredTotal',))
        cart_id = _id(cart['id'])
        if cart_id in ids:
            raise ValueError('Cart IDs must be unique.')
        ids.add(cart_id)
        items = cart['items']
        if not isinstance(items, list) or not 1 <= len(items) <= 100:
            raise ValueError('Each cart must contain 1–100 item lines.')
        item_ids, net = set(), 0
        for item in items:
            _object(item, ('id', 'unitPrice', 'quantity', 'discount'))
            item_id = _id(item['id'])
            if item_id in item_ids:
                raise ValueError('Item IDs must be unique within each cart.')
            item_ids.add(item_id)
            count = item['quantity']
            if type(count) is not int or not 1 <= count <= 100000:
                raise ValueError('Item quantity must be an integer from 1 to 100000.')
            subtotal = _units(item['unitPrice'], digits) * count
            discount = _units(item['discount'], digits)
            if discount > subtotal:
                raise ValueError('Line discount cannot exceed its subtotal.')
            net += subtotal - discount
        if _units(cart['orderDiscount'], digits) > net:
            raise ValueError('Order discount cannot exceed net item subtotal.')
        for field in _COSTS:
            if cart[field] is not None:
                _units(cart[field], digits)
        if 'declaredTotal' in cart:
            _units(cart['declaredTotal'], digits)
        inputs.append((cart_id, {'currency': value['currency'], 'minorUnitDigits': digits,
                                 **{key: data for key, data in cart.items() if key != 'id'}}))
    return [(cart_id, prepare_call('commerce.price-components', arguments,
                                   max_price_micro_usd=CALL_CEILING)) for cart_id, arguments in inputs]


def compare_results(plan, results):
    """Rank complete totals only. An incomplete cart prevents an overall winner."""
    if len(results) != len(plan):
        raise ValueError('Every planned cart needs a result before comparison.')
    ranked, incomplete, rows = [], [], []
    for (cart_id, call), result in zip(plan, results):
        source = json.loads(call.body)
        digits = source['minorUnitDigits']
        missing = [field for field in _COSTS if source[field] is None]
        if (not isinstance(result, dict) or result.get('currency') != source['currency']
                or type(result.get('minorUnitDigits')) is not int or result['minorUnitDigits'] != digits
                or result.get('missingComponents') != missing or 'total' not in result):
            raise ValueError('Unexpected reconciliation response; stop and preserve the original calls.')
        known = _units(result.get('knownTotal'), digits, result=True)
        total = result['total']
        if missing:
            if total is not None:
                raise ValueError('Incomplete cart cannot have a final total.')
            incomplete.append(cart_id)
        else:
            if _units(total, digits, result=True) != known:
                raise ValueError('Complete total does not match the reconciled known total.')
            ranked.append((known, cart_id))
        rows.append({'id': cart_id, 'total': total, 'knownTotal': result['knownTotal'],
                     'missingComponents': missing, 'matchesDeclaredTotal': result.get('matchesDeclaredTotal')})
    ranked.sort(key=lambda entry: entry[0])
    cheapest = [cart_id for total, cart_id in ranked if total == ranked[0][0]] if ranked else []
    return {'currency': json.loads(plan[0][1].body)['currency'], 'carts': rows,
            'completeRanking': [cart_id for _, cart_id in ranked], 'incompleteIds': incomplete,
            'cheapestCompleteIds': cheapest, 'overallCheapestIds': None if incomplete else cheapest,
            'scope': 'Supplied checkout snapshots only. Compare equivalent items and quantities. '
                     'Unknown costs are not zero; an incomplete cart prevents an overall winner. '
                     'No live price, inventory, tax-law, coupon eligibility or merchant-order verification.'}


def execute_comparison(plan, client, on_result):
    results = []
    for index, (cart_id, call) in enumerate(plan):
        response = client.execute(call)
        results.append(response['result'])
        # Reject a malformed result before spending on another candidate.
        compare_results(plan[:index + 1], results)
        on_result({'cartId': cart_id, 'requestId': call.request_id, **response})
    return compare_results(plan, results)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).with_name('cart_comparison_example.json'))
    parser.add_argument('--max-total-micro-usd', type=int, default=1000, help='Total ceiling, default $0.001; maximum $0.005')
    parser.add_argument('--execute', action='store_true', help='Authorize one capped call per cart using existing credits')
    args = parser.parse_args(argv)
    with args.input.open('rb') as handle:
        raw = handle.read(131073)
    if len(raw) > 131072:
        raise ValueError('Input exceeds 128 KiB.')
    plan = prepare_comparison(json.loads(raw), max_total_micro_usd=args.max_total_micro_usd)
    print(json.dumps({'mode': 'execute' if args.execute else 'offline-preview',
                      'maxNewDebitMicroUsd': sum(call.max_price_micro_usd for _, call in plan),
                      'calls': [{'cartId': cart_id, 'tool': call.tool_id, 'requestId': call.request_id,
                                 'maxPriceMicroUsd': call.max_price_micro_usd, 'input': json.loads(call.body)}
                                for cart_id, call in plan],
                      'note': 'Preview prepares requests; it does not compute totals or contact the service. '
                              'Retain this plan privately before execution. New runs create new billable IDs; '
                              'recover uncertain calls with their original IDs and inputs within ten minutes. '
                              'On any failure, later calls stop; earlier successful calls remain billable.'}), flush=True)
    if args.execute:
        def emit(response):
            print(json.dumps(response), flush=True)
        emit(execute_comparison(plan, Client(os.environ.get('AGENT_UTILITIES_API_KEY')), emit))


if __name__ == '__main__':
    try:
        main()
    except (CallError, ValueError, RuntimeError) as error:
        print(json.dumps({'error': str(error)}))
        raise SystemExit(1)
    except OSError:
        print(json.dumps({'error': 'Could not read the input file.'}))
        raise SystemExit(1)
