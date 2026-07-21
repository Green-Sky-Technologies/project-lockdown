#!/usr/bin/env node
/**
 * Sync the recall-gate wordlist from the CANONICAL core copy into a bundled TS
 * module (design doc §4.2: "the wordlist and the feedback pipeline are one loop").
 * One source of truth — the extension never hand-maintains its own copy.
 */
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '..', '..');
const src = resolve(repo, 'core', 'lockdown_core', 'wordlist', 'violence_to_others.txt');
const out = resolve(here, '..', 'src', 'generated', 'wordlist.ts');

const raw = await readFile(src, 'utf8');
const terms = raw
  .split('\n')
  .map((l) => l.trim())
  .filter((l) => l && !l.startsWith('#'))
  .map((l) => l.toLowerCase());

const banner =
  '// GENERATED from core/lockdown_core/wordlist/violence_to_others.txt — do not edit.\n' +
  '// Regenerate: npm run gen:wordlist\n';
await mkdir(dirname(out), { recursive: true });
await writeFile(out, `${banner}export const WORDLIST: string[] = ${JSON.stringify(terms, null, 2)};\n`);
console.log(`wrote ${terms.length} terms -> src/generated/wordlist.ts`);
