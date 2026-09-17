import assert from 'node:assert/strict';
import { readFile, copyFile, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const manifest = JSON.parse(await readFile('.cursor-plugin/plugin.json', 'utf8'));
const config = JSON.parse(await readFile('mcp.json', 'utf8'));
assert.equal(manifest.mcpServers, 'mcp.json');
assert.equal(manifest.variables.properties.AGENT_UTILITIES_API_KEY.default, '');
assert.deepEqual(Object.keys(config.mcpServers), ['agent-utilities']);
const server = config.mcpServers['agent-utilities'];
assert.equal(server.command, 'node');
assert.deepEqual(server.args, ['${CURSOR_PLUGIN_ROOT}/agent-utilities-mcp.mjs']);
assert.deepEqual(server.env, { AGENT_UTILITIES_API_KEY: '${AGENT_UTILITIES_API_KEY}' });
assert.equal(server.autoApprove, undefined);
assert.equal(manifest.hooks, undefined);
const root = await mkdtemp(join(tmpdir(), 'agent utilities cursor '));
let transport, client;
try {
  await copyFile('agent-utilities-mcp.mjs', join(root, 'agent-utilities-mcp.mjs'));
  // Resolve only the documented plugin-root and declared empty key variable.
  // This tests the package launch contract, not the Cursor application's parser.
  transport = new StdioClientTransport({ command: process.execPath,
    args: server.args.map(value => value.replace('${CURSOR_PLUGIN_ROOT}', root)),
    env: { AGENT_UTILITIES_API_KEY: manifest.variables.properties.AGENT_UTILITIES_API_KEY.default }, stderr: 'pipe' });
  client = new Client({ name: 'cursor-config-verification', version: '1' });
  await client.connect(transport);
  const catalog = await client.listTools();
  assert.ok(catalog.tools.some(tool => tool.name === 'commerce_pack_plan'));
  const result = await client.callTool({ name: 'commerce_gtin_validate', arguments: { code: '036000291452' } });
  assert.equal(result.isError, true);
  assert.ok(JSON.stringify(result).includes('No API key configured'));
  console.log(JSON.stringify({ cursorConfigurationLaunch: true, pathWithSpaces: true,
    tools: catalog.tools.length, noKeyDenied: true, paidCallsSent: 0, cursorApplicationTested: false }));
} finally {
  await client?.close(); await transport?.close(); await rm(root, { recursive: true, force: true });
}
