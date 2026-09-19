# Runnable cart cleanup recipe

Download the Node.js 22+ recipe, its checksum and sample JSON from [the workflow page](https://agent-utilities.agent-utilities.workers.dev/use-cases/normalize-prices-update-cart?utm_source=github). No npm install is required. The script includes the existing Agent Utilities MCP adapter and SDK.

From the download folder:

```sh
shasum -a 256 -c cart-workflow.mjs.sha256
node cart-workflow.mjs --preview cart-example.json
```

Preview validates and prints your input and planned steps locally. It does not contact the service, use a key or calculate the final result. Running without arguments previews the included sample. The checksum is served alongside the file and establishes consistency, not an independent signature.

The sample replaces €17.00 coffee with €16.49 and a €10.00 mug with €9.95. Its two coffee bags, one mug, €2 order discount and €4.99 shipping produce a known total of €45.92. Unknown tax keeps the final total null. `cart-example-output.json` is generated from the actual tool implementations at build time, without network requests or payments; it is an expected fixture, not a live receipt.

## Execute with prepaid credits

Obtain an API key and existing prepaid balance in the [workspace](https://agent-utilities.agent-utilities.workers.dev/billing?utm_source=github). Set `AGENT_UTILITIES_API_KEY` privately using your environment or secret manager. Never enter a recovery credential, put a key in a command argument or commit one to a file.

```sh
node cart-workflow.mjs --execute cart-example.json
```

This explicit command authorizes up to three separately billed operations: `commerce.money-parse`, `data.json-patch`, and `commerce.price-components`. Current total estimate: 1,300 micro-dollars, or $0.0013. The recipe checks public prices and key mode before starting, and refuses to start if the estimate has risen above 1,300. It requires server-enforced credit price limits and caps each call at its discovered price using X-Max-Credit-Micro-Usd. These three calls together cannot debit more than 1,300 micro-dollars. If a price rises after discovery, the service rejects that new reservation with HTTP 412 and no debit; the recipe stops without increasing the cap. Receipts contain actual debits. It never purchases credits, tops up or places a merchant order.

Results are newline-delimited JSON. `execution-start` shows the mode, discovered prices and maxTotalMicroUsd ceiling. Each `step-result` contains the exact request arguments, result, debit receipt and retry information. `workflow-complete` combines the normalized amounts, updated supplied snapshot and reconciliation. Keep output private because it contains your supplied cart data. If saving it, use a private directory and restrictive file permissions.

Completed calls remain charged if a later step fails. If a displayed price is invalid, parsing is still a successful billed check; the recipe stops before patching. Known missing tax, shipping or fees remain null and do not become zero.

## Recover a partial run

The existing MCP adapter automatically retries one uncertain HTTP exchange using the same debit identity. It does not retry the whole recipe. If a step still fails or is uncertain, execution stops and prints that step's result and original arguments.

Use `agent_utilities_retry` in your configured MCP client with the returned `requestId`, original MCP tool name and exact original arguments within ten minutes. Follow the [adapter recovery instructions](https://agent-utilities.agent-utilities.workers.dev/integrations/mcp?utm_source=github). Do not rerun `--execute` to recover: a new run generates new operations and can charge again for completed steps. The recipe does not automatically resume later steps; use the recovered output and documented mapping to continue in your MCP client.

There is no durable local journal. If the process exits before returning an ID, inspect your balance or contact support before repeating that operation. The script does not modify your input file or a merchant cart.

## Bring your own cart

Use the exact shape of `cart-example.json`:

- Declare one supported locale, currency and decimal scale. The caller establishes those facts; symbols alone do not prove currency.
- Supply 1–100 items with unique IDs and nonnegative exact decimal strings. Quantities are integers. Every cost is explicit; use null for unknown shipping, tax or fees.
- Supply 1–24 displayed prices. Each price ID must identify an existing item. Unlisted items keep their original price.
- The patch tests currency, scale, item ID and original unit price before each replacement. It applies to the supplied snapshot only.
- Input files are limited to 32 KiB. Unsupported fields and excessive decimal precision fail before paid calls.

The downloadable client code is MIT-licensed; bundled dependency licenses are in `CART-WORKFLOW-NOTICES.txt`. The hosted tools remain paid APIs. Local tests and fixture output do not establish a customer sale.
