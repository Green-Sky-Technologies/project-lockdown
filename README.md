# Project Lockdown

An **opt-in, disclosed guard in front of any chatbot** that flags conversations
plausibly indicating intent to harm others, and puts a **responsible adult**
(parent or school staff) in the moderator role rather than relying on the model
provider to police it.

This repository is the first-pass **end-to-end walking skeleton**. See
[`technical-design-doc.md`](technical-design-doc.md) for the full design; it is
the source of truth. The skeleton proves the most important design decision —
the **capture ↔ core boundary** — with:

- a thin **TypeScript Chromium (MV3) extension** that captures chat text across
  multiple chatbot hosts, runs a local recall gate, and renders a lock overlay;
- a stateless **Python detection core** (FastAPI) that classifies with a
  two-stage LLM pipeline and emits a **verdict object** — the single contract
  every surface renders from;
- a **LangGraph** async pipeline (scaffolded, stubbed nodes) and **LangSmith**
  tracing/eval scaffolding.

> **Disclosure first.** Monitoring is disclosed to the monitored person. This is
> not a covert surveillance tool, not an emergency-response system, and not a
> diagnosis. See the design doc §1 (non-goals) and §8 (privacy/legal).

## Scope of this skeleton

- **One category:** `VIOLENCE_TO_OTHERS`.
- **Multiple hosts:** `chatgpt.com`, `claude.ai`, `gemini.google.com`.
- **Notifications stubbed** — the payload is logged; Resend (email) + Twilio
  (SMS) drop in later behind the same `Notifier` interface.

## Layout

```
contract/    JSON Schema source of truth for the verdict + request; codegen to Pydantic & TS
core/        Python detection core (FastAPI /classify, classifier, notifier, LangGraph pipeline)
extension/   TypeScript Chromium MV3 extension (capture + recall gate + lock overlay)
eval/        LangSmith red-team recall/precision scaffold
```

## Quick start

See [`core/README.md`](core/README.md) and [`extension/README.md`](extension/README.md).

```bash
# 1. Contract -> generated code
python contract/codegen/gen_pydantic.py
node contract/codegen/gen_ts.mjs

# 2. Core
cd core && uv sync && cp .env.example .env   # add ANTHROPIC_API_KEY
uv run uvicorn lockdown_core.app:app --reload

# 3. Extension
cd extension && npm install && npm run build
# then load extension/dist as an unpacked extension at chrome://extensions
```
