# Detection core

Stateless FastAPI service. Text in → **verdict object** out (design doc §5). The
classifier hot path is a thin two-tier SDK call; LangGraph runs only the async
pipeline (`lockdown_core/pipeline`).

## Run

```bash
cd core
uv sync                 # or: python -m venv .venv && .venv/bin/pip install -e '.[dev]'
cp .env.example .env    # add ANTHROPIC_API_KEY, or set LOCKDOWN_USE_FAKE_CLASSIFIER=1
uv run uvicorn lockdown_core.app:app --reload
```

Without a key the service wires a **deterministic fake classifier** so the whole
pipeline runs offline.

## Try it

```bash
curl -s localhost:8000/classify -H 'content-type: application/json' -d '{
  "windowed_text": [{"role":"user","text":"I am going to shoot up the school tomorrow"}],
  "category_set": ["VIOLENCE_TO_OTHERS"],
  "client_metadata": {"chatbot_host":"chatgpt.com","capture_surface":"CHROMIUM_EXT","monitored_categories":["VIOLENCE_TO_OTHERS"]},
  "inline_tier2": true
}' | python -m json.tool
```

## Test

```bash
uv run pytest            # action table, contract parity, /classify, auth, persistence, architecture guard
```

## Auth + persistence (production)

`/classify` requires a Clerk session token unless `LOCKDOWN_REQUIRE_AUTH=false`
(local-dev escape hatch). Flagged verdicts are attributed to the Clerk account and
persisted to Neon. See `.env.example` for all vars. Run migrations against Neon:

```bash
DATABASE_URL='<neon pooled string>' uv run alembic upgrade head
```

The auth (`auth/`) and persistence (`persistence/`) modules are wired only at the
composition root (`app.py`) — `clerk_backend_api` and `sqlalchemy` are kept off the
classifier hot-path import graph (enforced by `tests/test_architecture.py`).

## Layout

| Path | Responsibility |
|---|---|
| `contract/verdict.py` | Pydantic mirror of `contract/verdict.schema.json` (contract §5) |
| `contract/actions.py` | The one place verdict → `recommended_action` thresholds live (§5.3) |
| `classify/service.py` | Tier-1 → lock → tier-2 orchestration; assembles the verdict |
| `classify/anthropic_classifier.py` | Real tier-1/tier-2 structured-output calls (LangSmith-traced) |
| `classify/fake.py` | Deterministic keyless classifier for tests/offline |
| `notify/` | `Notifier` protocol + logging stub (Resend/Twilio drop in later) |
| `pipeline/` | LangGraph async pipeline (stubbed nodes); protocol keeps it off the hot path |
