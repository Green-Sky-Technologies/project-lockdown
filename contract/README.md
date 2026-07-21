# The verdict contract

`verdict.schema.json` and `classify-request.schema.json` are the **single
sources of truth** for the shared contract (design doc §5). Everything else
renders from the verdict; get it right in one place.

## Why JSON Schema

The verdict schema is also the artifact **Anthropic structured outputs** consumes
on the classifier call, so the model's constrained-decoding schema is a
*projection* of the verdict schema: **contract == wire format == model output**,
aligned for free.

## Generated code (do not hand-edit)

Two hand-maintained mirrors are kept in lockstep with the schema and verified by
codegen:

| Target | File | Regenerate / verify |
|---|---|---|
| Python (Pydantic) | `core/lockdown_core/contract/verdict.py` | `python contract/codegen/gen_pydantic.py` |
| TypeScript | `extension/src/contract/verdict.ts` | `node contract/codegen/gen_ts.mjs` |

The codegen scripts run the standard generators (`datamodel-code-generator`,
`json-schema-to-typescript`) into a temp file and **diff** against the committed
mirror, failing CI on drift. Run with `--write` to regenerate in place.
