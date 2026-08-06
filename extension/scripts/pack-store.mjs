#!/usr/bin/env node
/**
 * Produce a Chrome Web Store upload package from a fresh build.
 *
 * The CWS assigns its own extension ID from the developer account's key, so the
 * manifest `key` field (which pins a stable ID for local *unpacked* loads) is
 * removed here — leaving it in can trip "invalid value for key". Everything else
 * is the normal production build. Output: extension/project-lockdown-ext-store.zip
 */
import { execFileSync } from 'node:child_process';
import { cp, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const dist = resolve(root, 'dist');
const store = resolve(root, 'dist-store');
const zip = resolve(root, 'project-lockdown-ext-store.zip');

// 1. Fresh production build (uses extension/.env for DEFAULT_CORE_URL/DASHBOARD_URL).
execFileSync(process.execPath, [resolve(here, 'build.mjs')], { stdio: 'inherit' });

// 2. Copy the build and strip `key` from its manifest.
await rm(store, { recursive: true, force: true });
await cp(dist, store, { recursive: true });
const manifestPath = resolve(store, 'manifest.json');
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
delete manifest.key;

// Drop dev-only localhost hosts — a packaged store build never talks to a local
// core, and CWS reviewers flag unnecessary/broad host permissions.
const isDevHost = (h) => h.startsWith('http://localhost');
manifest.host_permissions = (manifest.host_permissions ?? []).filter((h) => !isDevHost(h));
for (const cs of manifest.content_scripts ?? []) {
  cs.matches = (cs.matches ?? []).filter((m) => !isDevHost(m));
}

await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');

// 3. Zip the store dir's CONTENTS (not the dir itself — CWS wants manifest at root).
await rm(zip, { force: true });
execFileSync('zip', ['-qr', zip, '.'], { cwd: store });

console.log(`store package -> ${zip}  (manifest v${manifest.version}, key stripped)`);
