"""A fixed public GTIN example. Default is offline; execution must be explicit."""
import argparse
import json
import os
from agent_utilities import Client, CallError, prepare_call

parser = argparse.ArgumentParser(description=__doc__)
mode = parser.add_mutually_exclusive_group()
mode.add_argument('--discover', action='store_true', help='Read public tool metadata; no key or charge')
mode.add_argument('--execute', action='store_true', help='Spend at most 300 micro-USD from existing credits')
args = parser.parse_args()
try:
    if args.discover:
        print(json.dumps(Client().catalog()))
    else:
        call = prepare_call('commerce.gtin-validate', {'code': '036000291452'}, max_price_micro_usd=300)
        print(json.dumps({'mode': 'execute' if args.execute else 'offline-preview', 'tool': call.tool_id,
                          'requestId': call.request_id, 'maxPriceMicroUsd': call.max_price_micro_usd,
                          'input': json.loads(call.body), 'note': 'A new run creates a new ID. Preserve this ID and input for recovery; do not rerun after an uncertain result.'}), flush=True)
        if args.execute:
            print(json.dumps(Client(os.environ.get('AGENT_UTILITIES_API_KEY')).execute(call)))
except (CallError, ValueError, RuntimeError) as error:
    # Client exceptions contain only fixed messages, codes and request IDs.
    print(json.dumps({'error': str(error)}))
    raise SystemExit(1)
