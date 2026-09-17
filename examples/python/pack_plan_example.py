"""Three fixed pack-planning examples. Preview is offline; --execute spends credits."""
import argparse
import json
import os
from pathlib import Path
from agent_utilities import Client, CallError, prepare_call


def main(argv=None):
    cases = json.loads(Path(__file__).with_name('pack_plan_cases.json').read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=list(cases), default='unit-price-trap')
    parser.add_argument('--execute', action='store_true', help='Authorize one new call, capped at $0.0008')
    args = parser.parse_args(argv)
    case = cases[args.scenario]
    call = prepare_call('commerce.pack-plan', case['input'], max_price_micro_usd=800)
    print(json.dumps({
        'mode': 'execute' if args.execute else 'offline-preview',
        'scenario': args.scenario, 'tool': call.tool_id, 'requestId': call.request_id,
        'maxPriceMicroUsd': call.max_price_micro_usd, 'input': json.loads(call.body),
        'expectedResultSubset': case['expected'],
        'note': 'Expected values are fixed local fixtures, not a service response. '
                'A new run creates a new request ID. Keep this ID and exact input before execution; '
                'do not rerun after an uncertain result. Recover the original call within ten minutes.',
    }), flush=True)
    if args.execute:
        print(json.dumps(Client(os.environ.get('AGENT_UTILITIES_API_KEY')).execute(call)))


if __name__ == '__main__':
    try:
        main()
    except (CallError, ValueError, RuntimeError) as error:
        print(json.dumps({'error': str(error)}))
        raise SystemExit(1)
