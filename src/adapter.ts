import { createHash, randomUUID } from 'node:crypto';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { CallToolRequestSchema, CallToolResultSchema, ListToolsRequestSchema, ListToolsResultSchema, type CallToolResult } from '@modelcontextprotocol/sdk/types.js';

export const SERVICE_ORIGIN = 'https://agent-utilities.agent-utilities.workers.dev';
const RETRY_TOOL = 'agent_utilities_retry';
const REQUEST_PATTERN = /^\d{13}_[A-Za-z0-9_-]{16,80}$/;
const LIMIT = 131072;
const failure = (message: string): CallToolResult => ({ isError: true, content: [{ type: 'text', text: message }] });

async function boundedJson(response: Response): Promise<any> {
  if (!response.body) throw new Error('empty_response');
  const reader = response.body.getReader();
  let size = 0;
  const chunks: Uint8Array[] = [];
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 2097152) throw new Error('response_limit');
      chunks.push(value);
    }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } finally { await reader.cancel().catch(() => {}); }
}

// The CLI never accepts an origin override. Injected fetch is only for local fixtures.
export async function createAdapter(apiKey?: string, transportFetch: typeof fetch = fetch) {
  if (apiKey && !/^au_(live|test)_[a-f0-9]{64}$/.test(apiKey)) throw new Error('Invalid API key format. Use an API credential, not a recovery credential.');
  const discovery = await transportFetch(SERVICE_ORIGIN + '/mcp', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, redirect: 'error', signal: AbortSignal.timeout(15000),
    body: JSON.stringify({ jsonrpc: '2.0', id: 'catalog', method: 'tools/list' }),
  });
  if (!discovery.ok) throw new Error('Catalog unavailable. Try again later.');
  const catalog = ListToolsResultSchema.parse((await boundedJson(discovery)).result);
  if (catalog.nextCursor || catalog.tools.length > 500 || catalog.tools.some(t => t.name === RETRY_TOOL)) throw new Error('Unsupported catalog. Update the adapter.');
  if (catalog._meta?.['agent-utilities/creditPriceLimits'] !== true) throw new Error('Server price-limit support is required.');
  const prices = new Map<string, number>();
  for (const tool of catalog.tools) {
    const price = tool._meta?.['agent-utilities/priceMicroUsd'];
    if (typeof price !== 'number' || !Number.isSafeInteger(price) || price < 0 || price > 999999999999 || prices.has(tool.name)) {
      throw new Error('Catalog must contain unique tool names and valid integer credit prices.');
    }
    prices.set(tool.name, price);
  }
  const names = new Set(prices.keys());
  const server = new Server({ name: 'agent-utilities', version: '0.3.0' }, { capabilities: { tools: {} }, instructions:
    'Paid tools spend prepaid Agent Utilities credits. Review prices and get user approval for spending. Each new tool call is a new billable operation. On uncertain outcomes use agent_utilities_retry with the returned requestId and unchanged name and arguments within ten minutes; never repeat as a new operation. New calls are capped at the price discovered when this adapter started. The retry helper authorizes no new debit; an unreceived request is rejected. There is no total session budget. No card purchases or automatic top-ups are available through this adapter.' });
  // Remember identity, not raw inputs/results. Refuse overflow rather than forget an ID and risk another debit.
  const requests = new Map<string, { hash: string; id: string }>();
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [
    ...catalog.tools.map(t => ({ ...t, description: t.description + ' Each new call spends credits, capped at the startup catalog price. Use agent_utilities_retry after an uncertain outcome.',
      annotations: { ...t.annotations, readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true } })),
    { name: RETRY_TOOL, description: 'Recover a previous Agent Utilities call with its exact requestId, tool name and arguments. Within ten minutes, a completed request returns its result without another debit. A zero ceiling prevents new reservations; a request that never arrived is rejected without a new debit. This does not cancel any previous reservation. Do not invent a new ID or change the input.',
      inputSchema: { type: 'object' as const, properties: { requestId: { type: 'string', pattern: REQUEST_PATTERN.source }, name: { type: 'string' }, arguments: { type: 'object' } }, required: ['requestId', 'name', 'arguments'], additionalProperties: false },
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true } },
  ] }));

  async function invoke(name: string, args: Record<string, unknown>, id: string, ceiling: number): Promise<CallToolResult> {
    const body = JSON.stringify({ jsonrpc: '2.0', id, method: 'tools/call', params: { name, arguments: args } });
    if (Buffer.byteLength(body) > LIMIT) return failure('Input exceeds the 128 KiB request limit. No request was sent.');
    let status: number | undefined;
    // Every attempt retains the exact body, origin, credential and debit identity.
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const response = await transportFetch(SERVICE_ORIGIN + '/mcp', { method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + apiKey, 'Idempotency-Key': id, 'X-Max-Credit-Micro-Usd': String(ceiling) },
          body, redirect: 'error', signal: AbortSignal.timeout(15000) });
        status = response.status;
        const json = await boundedJson(response);
        if (response.ok && json.jsonrpc === '2.0' && json.id === id && !json.error) {
          const result = CallToolResultSchema.parse(json.result);
          return { ...result, content: [...result.content, { type: 'text', text: JSON.stringify({ requestId: id, recoveryExpiresAt: result._meta?.recoveryExpiresAt, receipt: result._meta?.receipt }) }],
            _meta: { ...result._meta, requestId: id } };
        }
        if (status >= 400 && status < 500 && status !== 408) {
          const code = typeof json.error?.code === 'string' && /^[a-z_]{1,60}$/.test(json.error.code) ? json.error.code : 'request_rejected';
          return failure(`Service rejected the request (${status}, ${code}). Request ID: ${id}. Resolve the error before retrying. For recovery, use agent_utilities_retry with this ID and the exact original name and arguments. Manage credits at ${SERVICE_ORIGIN}/billing.`);
        }
      } catch { /* Never print transport exceptions: they can contain credentials or input. */ }
      if (!attempt) await new Promise(resolve => setTimeout(resolve, 250));
    }
    return failure(`Outcome uncertain${status ? ' (HTTP ' + status + ')' : ''}. Credits may have been deducted. Request ID: ${id}. Use agent_utilities_retry with this ID and the exact original name and arguments within ten minutes. Do not call the original tool again with a new ID. If recovery expires, check your balance and contact support before repeating the work.`);
  }

  server.setRequestHandler(CallToolRequestSchema, async (request, extra) => {
    if (!apiKey) return failure(`No API key configured. Discovery is free. Set AGENT_UTILITIES_API_KEY in the MCP process environment; obtain it at ${SERVICE_ORIGIN}/billing. Never give the agent your recovery key.`);
    const args = request.params.arguments ?? {};
    if (request.params.name === RETRY_TOOL) {
      const { requestId, name, arguments: original } = args;
      if (Object.keys(args).length !== 3 || typeof requestId !== 'string' || !REQUEST_PATTERN.test(requestId) || typeof name !== 'string' || !names.has(name) || !original || typeof original !== 'object' || Array.isArray(original)) return failure('Recovery requires a valid requestId, original tool name, and original arguments object.');
      return invoke(name, original as Record<string, unknown>, requestId, 0);
    }
    if (!names.has(request.params.name)) return failure('Unknown tool. Refresh the catalog.');
    const encoded = JSON.stringify([request.params.name, args]);
    if (Buffer.byteLength(encoded) > LIMIT - 200) return failure('Input exceeds the request limit. No request was sent.');
    const hash = createHash('sha256').update(encoded).digest('hex');
    const identity = typeof extra.requestId + ':' + extra.requestId;
    let previous = requests.get(identity);
    if (previous && previous.hash !== hash) return failure('This MCP request ID was already used for different input. No new request was sent.');
    if (!previous) {
      if (requests.size >= 5000) return failure('Adapter session limit reached. Resolve pending requests, then restart the adapter.');
      previous = { hash, id: Date.now() + '_' + randomUUID() };
      requests.set(identity, previous);
    }
    return invoke(request.params.name, args, previous.id, prices.get(request.params.name)!);
  });
  return server;
}
