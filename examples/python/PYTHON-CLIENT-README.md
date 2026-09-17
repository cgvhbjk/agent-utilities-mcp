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

## Shopping example: choose whole packs

Download [pack_plan_example.py](https://agent-utilities.agent-utilities.workers.dev/downloads/pack_plan_example.py), [pack_plan_cases.json](https://agent-utilities.agent-utilities.workers.dev/downloads/pack_plan_cases.json) and their [script checksum](https://agent-utilities.agent-utilities.workers.dev/downloads/pack_plan_example.py.sha256) and [data checksum](https://agent-utilities.agent-utilities.workers.dev/downloads/pack_plan_cases.json.sha256). Keep them beside `agent_utilities.py`. They are also in the public repository's `examples/python` directory.

```sh
shasum -a 256 -c pack_plan_example.py.sha256
shasum -a 256 -c pack_plan_cases.json.sha256
python3 pack_plan_example.py
python3 pack_plan_example.py --scenario limited-stock
python3 pack_plan_example.py --scenario insufficient-stock
```

These commands make no network requests. They print fixed sample inputs and expected result subsets, not computed answers or evidence of a hosted execution. The three fixtures illustrate twelve interchangeable units: two six-packs cost $15.98; with only one six-pack available, a six-pack plus a ten-pack costs $19.98; with only one six-pack and no ten-packs available, the request is infeasible. Prices and inventory are fictional.

To execute one selected scenario using existing credits, set `AGENT_UTILITIES_API_KEY` privately and add `--execute`. A new call is capped at $0.0008. A valid infeasible result is also billable. Funding starts with a $5 credit pack, but no payment or account is needed to inspect these examples.

The script prints the request ID and exact input before execution. Retain them privately if execution needs recovery; rerunning the script creates a new billable identity. Use the original ID and input with `prepare_call` and `Client.execute` as described above. The example does not buy credits or place orders, verify stock, or account for shipping, tax or product equivalence. See the [whole-pack workflow](https://agent-utilities.agent-utilities.workers.dev/use-cases/choose-whole-packs) before adapting it.

## Compare delivered checkout totals

Download [compare_carts.py](https://agent-utilities.agent-utilities.workers.dev/downloads/compare_carts.py) and [cart_comparison_example.json](https://agent-utilities.agent-utilities.workers.dev/downloads/cart_comparison_example.json), plus their [script checksum](https://agent-utilities.agent-utilities.workers.dev/downloads/compare_carts.py.sha256) and [input checksum](https://agent-utilities.agent-utilities.workers.dev/downloads/cart_comparison_example.json.sha256). Keep them beside `agent_utilities.py`. These files also live in the public repository's `examples/python` folder.

```sh
shasum -a 256 -c compare_carts.py.sha256
shasum -a 256 -c cart_comparison_example.json.sha256
python3 compare_carts.py
```

The default command is offline. It validates the supplied inputs and prints the planned requests and price ceilings; it does not calculate the checkout totals, use a key or contact the service. The fictional example compares identical items: an $18 item plus $5.99 shipping and $1.50 tax totals $25.49; a $22 item with a $1 discount, free shipping and $1.50 tax totals $22.50. The second cart has the lower delivered total despite its higher item price.

Use `--input your-carts.json` for 2–10 comparable checkout snapshots. Follow the sample structure, use unique cart IDs, declare one currency and decimal scale, and supply explicit line and order discounts. Each line discount applies once to the entire line. Set unknown shipping, tax or fees to `null`, never zero. Establish equivalent products, quantities and eligible discounts before comparison. The recipe does not verify those facts, fetch merchant data or calculate taxes from local law.

Add `--execute` only when you want paid execution using existing credits. It sends one `commerce.price-components` call per cart, each capped at $0.0005. The default total ceiling is $0.001 for two carts; for three carts, explicitly supply `--max-total-micro-usd 1500`. The maximum is 5000 micro-dollars ($0.005) for ten carts. A candidate count exceeding the chosen ceiling is rejected before any requests. An unknown-cost result is still a successful, billable reconciliation.

The output retains every known subtotal and missing component. `completeRanking` orders only fully supplied checkout totals using exact integers. `cheapestCompleteIds` includes ties among complete carts; `overallCheapestIds` is `null` whenever any candidate is incomplete. It will not silently recommend a merchant by treating missing tax or shipping as free. A declared-total mismatch is reported alongside the computed total for review.

The script prints every prepared ID and exact input before execution, then emits each successful response and receipt. Preserve this plan privately: it may contain your shopping data. If any call fails or returns an unexpected result, later calls stop; earlier completed calls remain charged. This is not an atomic transaction. **Do not rerun `--execute` to recover an uncertain result.** Use the original tool, input and request ID from the printed plan with `prepare_call` and `Client.execute` within ten minutes, as described above. The recipe creates no durable journal, buys no credits and places no merchant orders.
