# Cursor plugin package

The repository includes `.cursor-plugin/plugin.json`, `mcp.json` and the bundled Node.js adapter. This is a local stdio plugin, not a remote MCP URL. Node.js 22+ must be on the client's PATH. There is no npm package to install and no automatic dependency-install hook.

The manifest follows [Cursor's plugin reference](https://cursor.com/docs/reference/plugins). The server path uses Cursor's `CURSOR_PLUGIN_ROOT` placeholder so the installed repository can live anywhere, including a path containing spaces. Other MCP clients should use the ordinary README installation instructions rather than this Cursor-specific configuration.

Leave the plugin's `AGENT_UTILITIES_API_KEY` variable empty for free tool discovery. For paid execution, configure an API key privately through the client's plugin settings. Never put the key into the repository or a shared project file, and never give the plugin your account recovery credential. Keep tool approvals enabled. Requests send inputs to Agent Utilities under its [data policy](https://agent-utilities.agent-utilities.workers.dev/policies).

Hosted execution uses prepaid credits: individual calls cost $0.0003–$0.002 and funding starts with a $5 pack. The current bundled adapter (0.3.0) caps new debits at startup catalog prices and uses zero for manual recovery. It has no total session budget. It never buys credits, automatically tops up, or places merchant orders. Discovery alone spends nothing. Preserve returned request IDs and original arguments for ten-minute recovery; a new tool call is a new billable identity.

Local verification validates the manifest against Cursor's published schema and launches the actual configuration through the official MCP SDK after resolving the documented placeholders. It confirms discovery and rejection of paid execution without a key. This is a configuration/stdio test, not an observed Cursor application installation or marketplace approval. No official Cursor or community-directory listing is claimed until separately verified.

## Local plugin setup

Clone the public repository into a folder under `~/.cursor/plugins/local/agent-utilities`, following [Cursor's local plugin instructions](https://cursor.com/docs/plugins). Configure the declared key variable privately if you intend to execute paid calls. This checkout contains the prebuilt adapter; no build step is required for Node.js 22+. Actual Cursor application installation remains unverified here.

## Standalone config for directory install links

A directory's “Add to Cursor” link may install only an MCP configuration, without downloading the plugin repository. Do not use `CURSOR_PLUGIN_ROOT` in that context. This separately verified config installs the standalone adapter from a pinned public Git commit through npm's GitHub support:

```json
{
  "command": "npx",
  "args": [
    "--yes",
    "--package=git+https://github.com/cgvhbjk/agent-utilities-mcp.git#09d4673c0a057cf1201649646fb1154f83106994",
    "agent-utilities-mcp"
  ],
  "env": { "AGENT_UTILITIES_API_KEY": "" }
}
```

This requires Node.js 22+, npm/npx, Git and network access. It downloads code from the public GitHub repository, not an npm registry release. The commit is the source of the v0.3.0 release. Tool discovery follows the current service catalog. The empty key intentionally permits free discovery only; set a valid key privately in the client's configuration for paid execution. Keep approvals enabled. This standalone config was launched successfully through the MCP SDK with no paid requests; the directory UI and Cursor application have not been tested end to end.
