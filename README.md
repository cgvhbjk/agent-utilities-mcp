# Agent Utilities MCP

Connect a local stdio MCP client to 36 paid utility APIs for HTML extraction, JSON validation, agent configuration checks and product data. This MIT-licensed adapter runs locally; the hosted API is a paid service.

[Tool catalog](https://agent-utilities.agent-utilities.workers.dev/tools) · [Installation guide](https://agent-utilities.agent-utilities.workers.dev/integrations/mcp) · [Pricing](https://agent-utilities.agent-utilities.workers.dev/pricing) · [Policies and support](https://agent-utilities.agent-utilities.workers.dev/policies)

VS Code users: [open the setup link and private-key configuration](https://agent-utilities.agent-utilities.workers.dev/integrations/mcp#vscode). [Detailed instructions](https://github.com/cgvhbjk/agent-utilities-mcp/blob/main/VSCODE.md) are included in this source repository.

## Pay per call with USDC

For agents with a Circle Gateway balance, a separate [standalone USDC client](https://agent-utilities.agent-utilities.workers.dev/integrations/crypto) supports Base mainnet payments without a $5 Stripe pack. [Download and preview the example](https://github.com/cgvhbjk/agent-utilities-mcp/tree/main/examples/crypto). It pins network and contracts, caps each call, and saves signed requests privately for recovery. Preview is offline; preparation and submission require separate explicit commands. Real execution spends real USDC. This client is separate from the Stripe-funded MCP adapter and is not included in the immutable MCPB 0.3.0 release.

## Try the shopping example without an account

Clone this repository and preview the supplied cart with Node.js 22+:

```sh
cd examples/cart
shasum -a 256 -c cart-workflow.mjs.sha256
node cart-workflow.mjs --preview cart-example.json
```

Preview validates the input and prints the three-step plan **offline**, with no API key, network request or charge. It does not execute the tools. The included [expected output](https://github.com/cgvhbjk/agent-utilities-mcp/blob/main/examples/cart/cart-example-output.json) is a local fixture: German price strings become decimal amounts, guarded patches update the supplied cart snapshot, and cost reconciliation returns a known total of **€45.92**. Tax is unknown, so the final total remains `null`.

To run those three operations against the hosted service, privately set `AGENT_UTILITIES_API_KEY` in your process environment and explicitly choose:

```sh
node cart-workflow.mjs --execute cart-example.json
```

Execution spends existing service credits. The recipe enforces per-call price ceilings totaling **at most $0.0013** (0.13 cents) across its three logical calls. It stops if a discovered price is too high or a later price exceeds the authorized ceiling. Completed steps stay charged if a later step fails. Each step returns its debit receipt and recovery information; do not rerun the entire recipe after an uncertain response. Read the [recipe instructions](https://github.com/cgvhbjk/agent-utilities-mcp/blob/main/examples/cart/CART-WORKFLOW-README.md) before execution. This example does not buy credits or place a merchant order.

The recipe is a separate standalone download, not part of the immutable v0.3.0 MCPB bundle. You can also get it from the [workflow page](https://agent-utilities.agent-utilities.workers.dev/use-cases/normalize-prices-update-cart). The generic MCP adapter's spending behavior remains as described below.

## Read the material directly from an agent

No account or key is needed to read contracts, examples, prices and guides:

```sh
curl --fail --silent --show-error \
  https://agent-utilities.agent-utilities.workers.dev/v1/content/index
```

- [Complete JSON content](https://agent-utilities.agent-utilities.workers.dev/v1/content): tool input/output schemas, example requests, execution headers, workflows and documentation.
- [Full text guide](https://agent-utilities.agent-utilities.workers.dev/llms-full.txt): the same material as plain text.
- [One tool's contract](https://agent-utilities.agent-utilities.workers.dev/v1/content/tools/commerce.money-parse): request schema, example, price and execution URL.
- [Cart workflow](https://agent-utilities.agent-utilities.workers.dev/v1/content/workflows/normalize-prices-update-cart): the steps and current aggregate price.
- [OpenAPI](https://agent-utilities.agent-utilities.workers.dev/openapi.json): HTTP tool operations, optional credit ceiling header and error responses.

These public GET endpoints support cross-origin browser reads. Tool execution remains paid. Custom HTTP clients can send `X-Max-Credit-Micro-Usd` to cap a new prepaid credit debit; read the [quickstart](https://agent-utilities.agent-utilities.workers.dev/quickstart) for retry semantics. Adapter 0.3.0 caps each new call at its startup catalog price and requires server-advertised support.

## Prefer Python?

The [Python HTTP client](https://agent-utilities.agent-utilities.workers.dev/integrations/python) uses only Python 3.10+ standard libraries. See [examples/python](https://github.com/cgvhbjk/agent-utilities-mcp/tree/main/examples/python) for offline preview, free discovery and explicit paid calls with per-call ceilings and stable retry identities. No Node or MCP process is required for this route. It is separate from the MCPB bundle.

## Install

Also listed on [Smithery](https://smithery.ai/servers/benjaminhelfand/agent-utilities) as a local Node.js MCPB bundle. Its download matches the v0.3.0 GitHub artifact. Connect the adapter for the complete current tool schemas and prices; directory metadata is a discovery summary.

For clients that support MCP bundles, download `agent-utilities-mcp-0.3.0.mcpb` and its checksum from the [v0.3.0 release](https://github.com/cgvhbjk/agent-utilities-mcp/releases/tag/v0.3.0). Verify the checksum before importing the bundle through your client's extension settings. It contains the adapter, manifest and license notices. The bundle is unsigned; the release checksum establishes file consistency, not an independent signature. Bundle schema and standalone execution are tested; installation in each desktop client is not verified.

The bundle's optional **Agent Utilities API key** setting is marked sensitive. Leave it empty for free discovery, or enter only your API key to enable paid calls. Node.js 22+ is required; use a compatible runtime provided by your client or installed locally. If your client cannot import MCPB files, use the manual setup below.

Requires Node.js 22 or newer. Download `agent-utilities-mcp.mjs` and its `.sha256` file from the installation guide, then verify the file from its folder:

```sh
shasum -a 256 -c agent-utilities-mcp.mjs.sha256
```

Alternatively, clone this repository and use its bundled `agent-utilities-mcp.mjs` directly. No npm install is needed to run the bundle. Source is in `src/`; `npm ci && npm run build` rebuilds it. The public bundle is tested as a standalone process outside the application's dependency tree.

For a client that uses the common `mcpServers` configuration format:

```json
{
  "mcpServers": {
    "agent-utilities": {
      "command": "node",
      "args": ["/absolute/path/agent-utilities-mcp.mjs"],
      "env": {
        "AGENT_UTILITIES_API_KEY": "YOUR_PRIVATE_API_KEY"
      }
    }
  }
}
```

Replace the file path. Configure the API key privately using the client's secret settings where supported; never commit a real key or paste it into an agent prompt. Use the absolute path to Node if the client cannot find it. Remote-only MCP clients cannot launch this stdio adapter.

Omit the key to discover tools without spending credits. Obtain an API key and separately saved recovery key in the [workspace](https://agent-utilities.agent-utilities.workers.dev/billing). Only give the API key to the adapter. Live mode sells $5 USD prepaid service credits. Check the displayed mode before buying.

## What it does

- Fetches the public tool definitions and current per-call prices on startup.
- Exposes the 36 service tools and one recovery helper. The recovery helper is not an additional product.
- Sends authenticated calls only to the fixed Agent Utilities origin; redirects are rejected.
- Generates a stable debit request ID and retries one failed HTTP exchange with the identical body and ID.
- Keeps request identities and input hashes in process memory, without logging inputs, results or credentials. Remote data handling is described in the service policies.
- Does not purchase credits, automatically top up, access a wallet or accept recovery credentials.

Try a useful task such as: “Use commerce_gtin_validate to check barcode 036000291452.” One successful call costs $0.0003. Current tool prices range from $0.0003 to $0.002; these are experimental prices, not fixed forever. Every new operation spends credits. Version 0.3.0 caps each new debit at the price discovered at startup. There is no total session budget; repeated new calls can spend the available balance. A higher server price returns HTTP 412 instead of increasing the ceiling. Restart only after reviewing refreshed prices. Review prices and approve spending in your client.

## Retry an uncertain result

Results and uncertain outcomes include a `requestId`. Call `agent_utilities_retry` with that ID, the original MCP tool name, and the original arguments:

```json
{
  "requestId": "COPY_THE_RETURNED_REQUEST_ID",
  "name": "commerce_gtin_validate",
  "arguments": { "code": "036000291452" }
}
```

Within ten minutes a completed request returns the saved result without another debit. In version 0.3.0 the recovery helper sends a zero ceiling: a request that never reached the service is rejected without a new reservation. This does not cancel a previous reservation or refund a charge. The automatic transport retry of a new call retains its original nonzero ceiling and can still execute that authorized operation once. Do not generate a new ID or change the input to recover an uncertain result. Expired request identities cannot make another debit. Reusing an MCP request ID within one process also retains its original debit identity.

After a process restart you need the returned request ID and original input for recovery. If the process died before your client received the ID, inspect the balance or contact support before repeating the operation. No durable local input or result history is stored. Each process retains up to 5,000 MCP request identities, then refuses new calls until restarted; finish pending recovery first.

## Service limits

The release allows 1,000 new paid calls per day across the service. Inputs are bounded to 128 KiB including protocol overhead. Network tools are restricted to the hosts shown in the catalog; they are not a general web browser. Security checks are heuristics. Successful results are encrypted for ten-minute retry recovery, with request tombstones retained for one day. See the policies for retention and refund details.

Automated tests verify lost-response recovery against a local Cloudflare credit ledger. They do not establish customer demand or prove a live customer purchase. Directory validation and free tool discovery are not sales.

## License

Adapter code: MIT. Bundled dependencies: see `THIRD-PARTY-NOTICES.txt`. The license covers the adapter, not free access to the hosted APIs.


## Choose whole packs for a shopping task

The [pack planner](https://agent-utilities.agent-utilities.workers.dev/tools/commerce.pack-plan) finds the minimum item subtotal for a required count of interchangeable items using explicit pack limits. Twelve items can cost $15.98 as two six-packs at $7.99, even when a ten-pack at $11.99 has a lower unit price. The operation costs $0.0008 in prepaid credits. Shipping, tax, coupons and product equivalence are outside its optimization.

Call `commerce_pack_plan` through MCP, or use the [Python client](https://agent-utilities.agent-utilities.workers.dev/integrations/python) with tool ID `commerce.pack-plan` and an explicit 800-micro-dollar ceiling. Inspect the [free JSON contract](https://agent-utilities.agent-utilities.workers.dev/v1/content/tools/commerce.pack-plan) before executing. The [worked workflow](https://agent-utilities.agent-utilities.workers.dev/use-cases/choose-whole-packs) explains stock limits and how pack counts map into cart reconciliation. The adapter discovers this tool from the service; new tools do not require replacing the adapter.

Try the [Python pack-planning example](examples/python/pack_plan_example.py) with its [three sample cases](examples/python/pack_plan_cases.json). Run `python3 pack_plan_example.py` from `examples/python`, or select `--scenario limited-stock` / `--scenario insufficient-stock`. The default is an offline display of fixed fixtures; it sends no request and computes no new answer. Adding `--execute` explicitly authorizes one hosted call capped at $0.0008 using existing credits. A valid infeasible result is billable too. See the [Python guide](https://agent-utilities.agent-utilities.workers.dev/integrations/python) for checksums, input limits and recovery before executing. Each new run creates a new ID; do not rerun to recover an uncertain paid result.

## Upgrading from 0.2.1

Install 0.3.0 for per-call price ceilings and recovery-only manual retries. Version 0.2.1 does not enforce these adapter protections. Existing 0.2.1 release bytes remain available and unchanged; upgrading requires replacing the installed adapter. The per-call ceiling does not limit the number of new calls or provide a total session budget.

### Compare delivered checkout totals

The standard-library Python recipe in `examples/python/compare_carts.py` compares supplied merchant checkout snapshots using one capped reconciliation per cart. Default preview is offline; execution requires `--execute` and existing credits. It ranks complete totals, retains ties and declines to name an overall winner when any cart has unknown shipping, tax or fees. The two-cart default ceiling is $0.001. See the [comparison guide](https://agent-utilities.agent-utilities.workers.dev/integrations/python#compare-carts) for sample inputs, checksums, explicit budgets and recovery.
