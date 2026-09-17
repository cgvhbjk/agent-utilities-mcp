import { build } from 'esbuild';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

export async function buildMcp() {
  const path = 'agent-utilities-mcp.mjs';
  const bundled = await build({ entryPoints: ['src/cli.ts'], bundle: true, platform: 'node', target: 'node22', format: 'esm', outfile: path, metafile: true,
    banner: { js: "#!/usr/bin/env node\nimport { createRequire as __createRequire } from 'node:module'; const require = __createRequire(import.meta.url);" }, legalComments: 'eof' });
  const sha256 = createHash('sha256').update(await readFile(path)).digest('hex');
  await writeFile(path + '.sha256', sha256 + '  agent-utilities-mcp.mjs\n');
  // Distribute the licenses of the libraries included by the SDK bundle.
  const packages = new Set(Object.keys(bundled.metafile.inputs).filter(p => p.startsWith('node_modules/')).map(p => {
    const parts = p.slice('node_modules/'.length).split('/'); return parts.slice(0, parts[0].startsWith('@') ? 2 : 1).join('/');
  }));
  const notices = await Promise.all([...packages].sort().map(async name => {
    for (const file of ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'license']) {
      try { return name + '\n' + await readFile('node_modules/' + name + '/' + file, 'utf8'); } catch { /* Try the next conventional filename. */ }
    }
    throw new Error('Missing bundled license for ' + name);
  }));
  await writeFile('THIRD-PARTY-NOTICES.txt', notices.join('\n\n'));
}

await buildMcp();
