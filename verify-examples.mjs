import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const directory = new URL('./examples/cart/', import.meta.url);
const script = new URL('cart-workflow.mjs', directory);
const checksum = (await readFile(new URL('cart-workflow.mjs.sha256', directory), 'utf8')).trim().split(/\s+/);
assert.equal(checksum[1], 'cart-workflow.mjs');
assert.equal(createHash('sha256').update(await readFile(script)).digest('hex'), checksum[0]);
// A preview must work with no credentials and fail if it attempts an HTTP fetch.
const guard = 'data:text/javascript,' + encodeURIComponent('globalThis.fetch = () => { throw new Error("Offline preview attempted HTTP"); };');
const output = execFileSync(process.execPath, ['--import', guard, fileURLToPath(script), '--preview', 'cart-example.json'], {
  cwd: directory, env: {}, encoding: 'utf8', timeout: 15000,
});
const preview = JSON.parse(output);
assert.equal(preview.mode, 'offline-preview');
assert.equal(preview.paidCallsSent, 0);
assert.deepEqual(preview.input, JSON.parse(await readFile(new URL('cart-example.json', directory), 'utf8')));
assert.deepEqual(preview.steps, ['commerce.money-parse', 'data.json-patch', 'commerce.price-components']);
const fixture = JSON.parse(await readFile(new URL('cart-example-output.json', directory), 'utf8'));
assert.match(fixture.source, /local fixture/);
assert.equal(fixture.reconciliation.knownTotal, '45.92');
assert.equal(fixture.reconciliation.total, null);
const base = 'https://agent-utilities.agent-utilities.workers.dev';
const read = async path => {
  const response = await fetch(base + path, { redirect: 'error', signal: AbortSignal.timeout(15000), headers: { 'X-Agent-Utilities-Check': '1' } });
  assert.equal(response.status, 200, path);
  return response.json();
};
const index = await read('/v1/content/index');
assert.ok(index.tools.some(t => t.id === 'commerce.money-parse'));
const contract = await read('/v1/content/tools/commerce.money-parse');
assert.equal(contract.execution.optionalHeaders['X-Max-Credit-Micro-Usd'], String(contract.priceMicroUsd));
assert.equal((await read('/billing/api/status')).creditPriceLimits, true);
console.log(JSON.stringify({ recipeChecksum: checksum[0], offlinePreview: true, publicContent: true, paidCallsSent: 0 }));
