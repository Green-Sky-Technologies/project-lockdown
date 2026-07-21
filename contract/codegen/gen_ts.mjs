#!/usr/bin/env node
/**
 * Generate a *reference* TypeScript type from the verdict schema.
 *
 * The committed mirror at `extension/src/contract/verdict.ts` is hand-maintained
 * (it carries doc comments, request types from a second schema, and the shared
 * decision helpers) — so we do NOT text-diff against a generator. This emits a
 * reference `.d.ts` you can eyeball when changing the schema.
 *
 *   node contract/codegen/gen_ts.mjs   // -> contract/codegen/_generated/verdict_ref.d.ts
 *
 * Requires: `npm i -D json-schema-to-typescript` (dev dep of the extension).
 */
import { compileFromFile } from 'json-schema-to-typescript';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '..', '..');
const schema = resolve(repo, 'contract', 'verdict.schema.json');
const out = resolve(repo, 'contract', 'codegen', '_generated', 'verdict_ref.d.ts');

const ts = await compileFromFile(schema, { additionalProperties: false, bannerComment: '' });
await mkdir(dirname(out), { recursive: true });
await writeFile(out, ts);
console.log(`wrote reference type ${out}`);
console.log('The committed mirror is extension/src/contract/verdict.ts.');
