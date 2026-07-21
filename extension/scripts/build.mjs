#!/usr/bin/env node
/** Build the unpacked extension into dist/. */
import { execFileSync } from 'node:child_process';
import { cp, mkdir, rm } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as esbuild from 'esbuild';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const dist = resolve(root, 'dist');

// 1. Sync the wordlist from the canonical core copy.
execFileSync(process.execPath, [resolve(here, 'gen-wordlist.mjs')], { stdio: 'inherit' });

// 2. Fresh dist.
await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

// 3. Bundle. Content script as IIFE (injected into the page); background as an
//    ES module (manifest declares "type": "module").
const common = { bundle: true, target: 'es2020', logLevel: 'info' };
await esbuild.build({
  ...common,
  entryPoints: [resolve(root, 'src/content/index.ts')],
  outfile: resolve(dist, 'content.js'),
  format: 'iife',
});
await esbuild.build({
  ...common,
  entryPoints: [resolve(root, 'src/background/worker.ts')],
  outfile: resolve(dist, 'background.js'),
  format: 'esm',
});

// 4. Static assets.
await cp(resolve(root, 'manifest.json'), resolve(dist, 'manifest.json'));

console.log('built extension -> dist/ (load unpacked at chrome://extensions)');
