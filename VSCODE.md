# Agent Utilities in VS Code

Use Agent Utilities with VS Code's built-in MCP support and a chat session that supports MCP tools. Node.js 22+, npm/npx and Git must be on the machine where the server runs. The configuration downloads the standalone adapter from the immutable GitHub source of release 0.3.0. It does not install an npm registry package.

## Install

Open the [VS Code setup section](https://agent-utilities.agent-utilities.workers.dev/integrations/mcp#vscode) and select **Set up in VS Code**. Your browser may ask to open the desktop application. Review the configuration, choose where to install it and confirm trust before starting the server. The link contains a private-input placeholder, never a credential. It does not approve tool execution or purchase credits.

If the link does not open your application, download [the VS Code configuration](https://agent-utilities.agent-utilities.workers.dev/downloads/vscode-mcp.json). Run **MCP: Open User Configuration** in VS Code's Command Palette. Merge the downloaded `inputs` and `servers` entries with your existing configuration; do not overwrite other servers. For a project-specific installation, merge into `.vscode/mcp.json`. This uses `servers`, unlike the `mcpServers` format used by some other clients.

When prompted, leave the API key empty to discover the tools for free. To execute paid calls, create an account in the [API workspace](https://agent-utilities.agent-utilities.workers.dev/billing), save both credentials privately and fund service credits. Enter only the API key in VS Code's private input prompt; keep the account recovery credential separate. VS Code stores the input for reuse. If you previously left it blank, edit that stored input before restarting the server. Never paste a key into chat, the install URL or a shared configuration file.

## A first task

Start the server using **MCP: List Servers**, then choose its tools in Chat's tool picker. For a first paid task, ask:

> Use commerce_gtin_validate once to check barcode 036000291452.

Review the tool and price before approving execution. That tool costs $0.0003 per successful call; credit funding starts at $5. Keep per-tool approvals enabled. Adapter 0.3.0 caps each new debit at its startup catalog price, but it has no total session budget and never automatically buys credits. Each new call is a new billable operation.

For an uncertain result, preserve the returned request ID and original input. Use `agent_utilities_retry` within ten minutes. The helper can recover an existing matching request without authorizing a new reservation; it cannot cancel a previous reservation. Do not repeat the original tool with a new ID to recover it.

## Compatibility and verification

This configuration targets VS Code's built-in MCP support. It does not configure separate third-party chat extensions. VS Code documents that interactive input variables are not forwarded to Agent Host sessions; use a supported built-in session for this prompted setup. Browser-only clients also need an environment capable of launching the local Node.js process. For remote workspaces, install Node/npm/Git where the MCP server will actually run.

The encoded link, configuration fields and pinned command are checked. The official MCP SDK verifies startup, tool discovery and rejection of execution without an API key. Actual VS Code application installation and chat execution have not been tested; no VS Code Marketplace listing or endorsement is claimed. No live paid requests are used for these checks.

References: [VS Code installation links](https://code.visualstudio.com/api/extension-guides/ai/mcp), [configuration and private inputs](https://code.visualstudio.com/docs/agents/reference/mcp-configuration), [adding and managing servers](https://code.visualstudio.com/docs/agent-customization/mcp-servers).
