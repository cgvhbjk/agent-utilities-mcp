import assert from 'node:assert/strict';
import { mkdtemp,writeFile,rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join,resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
const dir=await mkdtemp(join(tmpdir(),'crypto-preview-'));
try {
  const guard=join(dir,'no-network.mjs');
  await writeFile(guard,"globalThis.fetch=async()=>{throw Error('Preview must not contact the network');};");
  const module=pathToFileURL(resolve('examples/crypto/agent-utilities-crypto.mjs')).href;
  execFileSync(process.execPath,['--import',guard,'--input-type=module','--eval',`const m=await import(${JSON.stringify(module)});for(const name of ['prepareCall','sendPrepared','privateKeyToAccount'])if(typeof m[name]!=='function')throw Error('Missing export');`],{env:{},timeout:15000});
  const result=JSON.parse(execFileSync(process.execPath,['--import',guard,resolve('examples/crypto/crypto-example.mjs'),'--preview'],{env:{},encoding:'utf8',timeout:15000}));
  assert.equal(result.mode,'offline-preview');assert.equal(result.paidCallsSent,0);assert.equal(result.signaturesCreated,0);assert.equal(result.maxMicroUsdc,300);assert.equal(result.network,'eip155:8453');
  console.log('Standalone crypto import and offline preview passed. No payment or signature.');
} finally {await rm(dir,{recursive:true,force:true});}
