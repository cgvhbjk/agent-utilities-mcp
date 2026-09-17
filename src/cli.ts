import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createAdapter } from './adapter';

try {
  const server = await createAdapter(process.env.AGENT_UTILITIES_API_KEY);
  await server.connect(new StdioServerTransport());
} catch {
  // Keep stdout exclusively MCP, and never echo credentials or remote error text.
  process.stderr.write('Agent Utilities could not start. Check Node.js 22+, network access and AGENT_UTILITIES_API_KEY format.\n');
  process.exitCode = 1;
}
