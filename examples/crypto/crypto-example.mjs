import { open, readFile } from 'node:fs/promises';
import { prepareCall, sendPrepared, privateKeyToAccount } from './agent-utilities-crypto.mjs';

const origin = 'https://agent-utilities.agent-utilities.workers.dev';
const input = { code: '036000291452' };
const [mode = '--preview', statePath] = process.argv.slice(2);
if (mode === '--preview') {
  console.log(JSON.stringify({ mode: 'offline-preview', tool: 'commerce.gtin-validate', input,
    network: 'eip155:8453', maxMicroUsdc: 300, maxUsdc: '0.0003', signaturesCreated: 0, paidCallsSent: 0 }, null, 2));
} else if (mode === '--prepare') {
  if (!statePath) throw Error('Provide a new private state file path. Preparation signs, but does not send payment.');
  const key = process.env.BUYER_PRIVATE_KEY, recipient = process.env.PAYMENT_RECIPIENT;
  if (!/^0x[\da-f]{64}$/i.test(key || '') || !/^0x[\da-f]{40}$/i.test(recipient || ''))
    throw Error('Set BUYER_PRIVATE_KEY and the independently approved PAYMENT_RECIPIENT privately.');
  if (process.env.PAYMENT_NETWORK !== 'eip155:8453') throw Error('Explicitly set PAYMENT_NETWORK=eip155:8453 for this real-USDC example.');
  // Claim the path before signing. Existing files are never overwritten.
  const file = await open(statePath, 'wx', 0o600);
  try {
    const prepared = await prepareCall({ url: origin + '/v1/tools/commerce.gtin-validate', body: input,
      account: privateKeyToAccount(key), expectedNetwork: 'eip155:8453', expectedRecipient: recipient, maxMicroUsdc: 300 });
    await file.writeFile(JSON.stringify(prepared)); await file.sync();
  } finally { await file.close(); }
  console.log('Saved the signed request privately. No payment sent. Use --send with this same file within five minutes.');
} else if (mode === '--send') {
  if (!statePath) throw Error('Provide the existing private state file. This command may spend up to 0.0003 USDC.');
  const prepared = JSON.parse(await readFile(statePath, 'utf8'));
  if (prepared.url !== origin + '/v1/tools/commerce.gtin-validate' || prepared.body !== JSON.stringify(input) ||
      typeof prepared.headers?.['PAYMENT-SIGNATURE'] !== 'string' || typeof prepared.headers?.['X-Quote'] !== 'string' ||
      typeof prepared.headers?.['X-Quote-Signature'] !== 'string') throw Error('This file is not a prepared GTIN example request.');
  // No key or signing is used here. Repeating this command sends identical authorization.
  try {
    const response = await sendPrepared(prepared);
    const data = await response.json();
    console.log(JSON.stringify({ httpStatus: response.status, ...data }, null, 2));
    if (!response.ok) process.exitCode = 1;
  } catch {
    console.error('Response unavailable. Keep this file and retry --send with it. Do not prepare a new payment.');
    process.exitCode = 1;
  }
} else {
  throw Error('Use --preview, --prepare <private-state-file>, or --send <private-state-file>.');
}
