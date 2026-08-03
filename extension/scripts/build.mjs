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
// Auth is a device token pasted at runtime — nothing secret is baked in.
const DEFAULT_CORE_URL = process.env.DEFAULT_CORE_URL || 'http://localhost:8000';
// Dashboard origin — where the popup sends the parent to generate a device token.
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:3000';

// 1. Sync the wordlist from the canonical core copy.
execFileSync(process.execPath, [resolve(here, 'gen-wordlist.mjs')], { stdio: 'inherit' });

// 2. Fresh dist.
await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

// 3. Bundle. Content script as IIFE (injected into the page); background + popup
//    as ES modules. No Clerk SDK — auth is a stored device token, so bundles stay tiny.
const define = {
  __DEFAULT_CORE_URL__: JSON.stringify(DEFAULT_CORE_URL),
  __DASHBOARD_URL__: JSON.stringify(DASHBOARD_URL),
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
