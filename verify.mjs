import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
const docker = process.argv.includes('--docker');
const transport = new StdioClientTransport({
  command: docker ? 'docker' : process.execPath,
  args: docker ? ['run', '--rm', '-i', 'agent-utilities-mcp'] : ['agent-utilities-mcp.mjs'],
  env: { AGENT_UTILITIES_API_KEY: '' }, stderr: 'pipe',
});
const client = new Client({ name: 'public-discovery-ci', version: '1' });
try {
  await client.connect(transport);
  const catalog = await client.listTools();
  assert.ok(catalog.tools.some(t => t.name === 'commerce_gtin_validate'));
  assert.ok(catalog.tools.some(t => t.name === 'agent_utilities_retry'));
  const rejected = await client.callTool({ name: 'commerce_gtin_validate', arguments: { code: '036000291452' } });
  assert.equal(rejected.isError, true);
  assert.ok(JSON.stringify(rejected).includes('No API key configured'));
  console.log(JSON.stringify({ transport: docker ? 'docker-stdio' : 'node-stdio', discovered: catalog.tools.length, noKeyDenied: true, paidCallsSent: 0 }));
} finally { await client.close(); await transport.close(); }
