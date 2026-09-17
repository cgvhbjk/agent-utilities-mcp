import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const config = JSON.parse(await readFile(process.argv[2] || 'vscode-mcp.json', 'utf8'));
assert.deepEqual(Object.keys(config), ['inputs', 'servers']);
assert.deepEqual(Object.keys(config.servers), ['agent-utilities']);
const input = config.inputs[0];
assert.equal(config.inputs.length, 1);
assert.equal(input.type, 'promptString');
assert.equal(input.password, true);
assert.equal(input.default, '');
const server = config.servers['agent-utilities'];
assert.deepEqual(Object.keys(server), ['type', 'command', 'args', 'env']);
assert.equal(server.type, 'stdio');
assert.equal(server.command, 'npx');
assert.equal(server.env.AGENT_UTILITIES_API_KEY, '${input:' + input.id + '}');
assert.deepEqual(server.args, ['--yes', '--package=git+https://github.com/cgvhbjk/agent-utilities-mcp.git#09d4673c0a057cf1201649646fb1154f83106994', 'agent-utilities-mcp']);
// Resolve the documented empty private input for a no-key subprocess check.
// This does not emulate VS Code's trust dialog or its credential storage.
const transport = new StdioClientTransport({ command: server.command, args: server.args,
  env: { PATH: process.env.PATH, HOME: process.env.HOME, AGENT_UTILITIES_API_KEY: input.default }, stderr: 'inherit' });
const client = new Client({ name: 'vscode-config-verification', version: '1' });
try {
  await client.connect(transport);
  assert.equal(client.getServerVersion().version, '0.3.0');
  const catalog = await client.listTools();
  assert.ok(catalog.tools.some(tool => tool.name === 'commerce_pack_plan'));
  const result = await client.callTool({ name: 'commerce_gtin_validate', arguments: { code: '036000291452' } });
  assert.equal(result.isError, true);
  assert.ok(JSON.stringify(result).includes('No API key configured'));
  console.log(JSON.stringify({ configurationLaunch: true, adapterVersion: '0.3.0',
    tools: catalog.tools.length, privateInputDefaultEmpty: true, noKeyExecutionDenied: true,
    paidCallsSent: 0, vscodeApplicationTested: false }));
} finally { await client.close(); await transport.close(); }
