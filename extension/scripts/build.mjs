#!/usr/bin/env node
/** Build the unpacked extension into dist/. */
import { execFileSync } from 'node:child_process';
import { cp, mkdir, readFile, rm } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as esbuild from 'esbuild';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const dist = resolve(root, 'dist');

// Load build-time config from extension/.env (gitignored) if present, so secrets
// aren't pasted on the command line. Existing process.env wins. See .env.example.
async function loadDotenv(path) {
  try {
    for (const line of (await readFile(path, 'utf8')).split('\n')) {
      const m = line.match(/^\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$/);
      if (m && !line.trimStart().startsWith('#') && process.env[m[1]] === undefined) {
        process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
      }
    }
  } catch {
    /* no .env — fine, use defaults / real env */
  }
}
await loadDotenv(resolve(root, '.env'));

// Build-time config (no secrets in source). Override via extension/.env or env.
const CLERK_PUBLISHABLE_KEY = process.env.CLERK_PUBLISHABLE_KEY || 'pk_test_REPLACE_ME';
const SYNC_HOST = process.env.SYNC_HOST || 'http://localhost:3000';
const DEFAULT_CORE_URL = process.env.DEFAULT_CORE_URL || 'http://localhost:8000';

if (CLERK_PUBLISHABLE_KEY === 'pk_test_REPLACE_ME') {
  console.warn('[build] CLERK_PUBLISHABLE_KEY not set — auth will not work until you set it.');
}

// 1. Sync the wordlist from the canonical core copy.
execFileSync(process.execPath, [resolve(here, 'gen-wordlist.mjs')], { stdio: 'inherit' });

// 2. Fresh dist.
await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

// 3. Bundle. Content script as IIFE (injected into the page); background + popup
//    as ES modules. Clerk (in background/popup) expects a browser-ish global env.
const define = {
  __CLERK_PUBLISHABLE_KEY__: JSON.stringify(CLERK_PUBLISHABLE_KEY),
  __SYNC_HOST__: JSON.stringify(SYNC_HOST),
  __DEFAULT_CORE_URL__: JSON.stringify(DEFAULT_CORE_URL),
  'process.env.NODE_ENV': JSON.stringify('production'),
  global: 'globalThis',
};
const common = { bundle: true, target: 'es2020', logLevel: 'info', define };

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
await esbuild.build({
  ...common,
  entryPoints: [resolve(root, 'src/popup/popup.ts')],
  outfile: resolve(dist, 'popup.js'),
  format: 'esm',
});

// 4. Static assets.
await cp(resolve(root, 'manifest.json'), resolve(dist, 'manifest.json'));
await cp(resolve(root, 'src/popup/popup.html'), resolve(dist, 'popup.html'));

console.log('built extension -> dist/ (load unpacked at chrome://extensions)');
