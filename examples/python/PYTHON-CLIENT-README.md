# Use Agent Utilities from Python

Use Python 3.10 or newer with the standard library client. No pip package, Node runtime or MCP process is required. Discovery and documentation are free; tool execution spends existing prepaid credits. This client cannot purchase credits, automatically top up or place merchant orders.

Download `agent_utilities.py`, `agent_utilities.py.sha256` and `agent_utilities_example.py` from `/integrations/python`, or use `examples/python` in the [public repository](https://github.com/cgvhbjk/agent-utilities-mcp/tree/main/examples/python). Keep the two Python files in the same directory. The client is MIT licensed; the license does not provide free hosted execution.

Verify the client, then preview the supplied barcode example without a network request or API key:

```sh
shasum -a 256 -c agent_utilities.py.sha256
python3 agent_utilities_example.py
```

The preview describes a possible request; it does not validate the barcode. The example's `--discover` option reads public content without authentication or payment.

## Discover contracts without a key

```python
from agent_utilities import Client

client = Client()
catalog = client.catalog()  # Free GET /v1/content; no Authorization header
status = client.status()    # Free current payment mode and capabilities
```

The catalog contains schemas, prices, examples, workflows and documentation. All operations are bounded; follow each tool's input contract. This client transports JSON but does not locally implement the full JSON Schema validator. The service validates inputs before execution.

## Prepare once, execute explicitly

Create and save your API and recovery credentials in the [workspace](https://agent-utilities.agent-utilities.workers.dev/billing), and buy credits only when you have useful work to run. Give your process only the API key through private environment configuration. Never include keys in source, command-line arguments, logs or agent prompts.

```python
import os
from agent_utilities import Client, prepare_call, CallError

client = Client(os.environ['AGENT_UTILITIES_API_KEY'])
call = prepare_call(
    'commerce.gtin-validate',
    {'code': '036000291452'},
    max_price_micro_usd=300,  # Maximum new debit: $0.0003
)
# Retain `call` before sending: it contains the fixed input, ID and ceiling.
try:
    response = client.execute(call)
except CallError as error:
    # error.call is the SAME prepared operation, including its request ID.
    # Stop new work, inspect error.code, and recover this call if appropriate.
    # Do not prepare a replacement operation after an uncertain outcome.
    raise
```

A successful response contains `result`, `receipt.chargedMicroUsd` and `recoveryExpiresAt`. The client checks mode and the server's price-limit capability before a paid call. Every new call must specify an integer ceiling from zero to 999999999999. HTTP 412 rejects a new reservation above that ceiling; the client never raises it automatically.

The example script's `--execute` option explicitly authorizes the supplied barcode call, capped at 300 micro-dollars. Each new script run creates a new request ID, so **do not rerun that command to recover a lost response**.

## Retry without a new charge identity

`execute(call)` makes at most two HTTP attempts for uncertain transport/server failures. Both use the same bytes, ID and ceiling. It rejects redirects and sends credentials only to the fixed service origin. Ordinary 4xx errors stop without automatic retry; HTTP 408 may be retried once.

If the outcome remains uncertain, preserve the `CallError.call` object. Retry with `client.execute(call)` within ten minutes, after addressing any returned error. A completed operation returns its stored result without another debit. A request that never arrived can execute and debit once up to its ceiling. A rejected retry does not prove that an earlier attempt was uncharged. Expired recovery requires checking the balance or contacting support before repeating work.

For recovery after a process restart, supply the original `request_id` to `prepare_call` with the same tool, input and ceiling. Persist these values privately before executing if your application needs crash recovery. They can contain sensitive input. The library does not write a journal or store credentials on disk, and it cannot recover an ID your application lost.

A ceiling of zero permits recovery of a matching existing reservation without authorizing a new debit. It does not refund or cancel a previous charge. Server recovery still binds the same tool version, price and input. Read the [developer quickstart](https://agent-utilities.agent-utilities.workers.dev/quickstart) for service limits and recovery details.
