# Agent Utilities MCP

Connect a local stdio MCP client to 33 paid utility APIs for HTML extraction, JSON validation, agent configuration checks and product data. This MIT-licensed adapter runs locally; the hosted API is a paid service.

[Tool catalog](https://agent-utilities.agent-utilities.workers.dev/tools) · [Installation guide](https://agent-utilities.agent-utilities.workers.dev/integrations/mcp) · [Pricing](https://agent-utilities.agent-utilities.workers.dev/pricing) · [Policies and support](https://agent-utilities.agent-utilities.workers.dev/policies)

## Install

For clients that support MCP bundles, download `agent-utilities-mcp-0.2.1.mcpb` and its checksum from the [v0.2.1 release](https://github.com/cgvhbjk/agent-utilities-mcp/releases/tag/v0.2.1). Verify the checksum before importing the bundle through your client's extension settings. It contains the adapter, manifest and license notices. The bundle is unsigned; the release checksum establishes file consistency, not an independent signature. Bundle schema and standalone execution are tested; installation in each desktop client is not verified.

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
- Exposes the 33 service tools and one recovery helper. The recovery helper is not an additional product.
- Sends authenticated calls only to the fixed Agent Utilities origin; redirects are rejected.
- Generates a stable debit request ID and retries one failed HTTP exchange with the identical body and ID.
- Keeps request identities and input hashes in process memory, without logging inputs, results or credentials. Remote data handling is described in the service policies.
- Does not purchase credits, automatically top up, access a wallet or accept recovery credentials.

Try a useful task such as: “Use commerce_gtin_validate to check barcode 036000291452.” One successful call costs $0.0003. Current tool prices range from $0.0003 to $0.002; these are experimental prices, not fixed forever. Every new operation spends credits. There is no adapter spending cap beyond the account's prepaid balance. Review prices and approve spending in your client.

## Retry an uncertain result

Results and uncertain outcomes include a `requestId`. Call `agent_utilities_retry` with that ID, the original MCP tool name, and the original arguments:

```json
{
  "requestId": "COPY_THE_RETURNED_REQUEST_ID",
  "name": "commerce_gtin_validate",
  "arguments": { "code": "036000291452" }
}
```

Within ten minutes a completed request returns the saved result without another debit. A request that never reached the service can execute and debit once. Do not generate a new ID or change the input to recover an uncertain result. Expired request identities cannot make another debit. Reusing an MCP request ID within one process also retains its original debit identity.

After a process restart you need the returned request ID and original input for recovery. If the process died before your client received the ID, inspect the balance or contact support before repeating the operation. No durable local input or result history is stored. Each process retains up to 5,000 MCP request identities, then refuses new calls until restarted; finish pending recovery first.

## Service limits

The release allows 1,000 new paid calls per day across the service. Inputs are bounded to 128 KiB including protocol overhead. Network tools are restricted to the hosts shown in the catalog; they are not a general web browser. Security checks are heuristics. Successful results are encrypted for ten-minute retry recovery, with request tombstones retained for one day. See the policies for retention and refund details.

Automated tests verify lost-response recovery against a local Cloudflare credit ledger. They do not establish customer demand or prove a live customer purchase. Directory validation and free tool discovery are not sales.

## License

Adapter code: MIT. Bundled dependencies: see `THIRD-PARTY-NOTICES.txt`. The license covers the adapter, not free access to the hosted APIs.
