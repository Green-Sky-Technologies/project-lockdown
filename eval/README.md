# Eval — standing red-team recall (design doc §7, §9)

False negatives are invisible by construction: the pipeline only ever sees
flagged-confirmed and flagged-cleared; *missed entirely* never enters the funnel.
So we generate misses deliberately and measure **recall** against them — the
number that matters most for a safety tool, and the hardest to see.

- `datasets/redteam_recall.jsonl` — oblique-intent phrasings (grow this over
  time; it is the honest false-negative estimate).
- `run_eval.py` — runs the **same** classify path the extension hits (reuses the
  core's `build_service`) and reports recall/precision. `--push` uploads the set
  to LangSmith, whose datasets + eval tooling is where this lives long-term.

```bash
# offline (uses the fake classifier if no ANTHROPIC_API_KEY)
LOCKDOWN_USE_FAKE_CLASSIFIER=1 python eval/run_eval.py

# against the real classifier + upload the dataset to LangSmith
ANTHROPIC_API_KEY=... LANGSMITH_API_KEY=... python eval/run_eval.py --push
```

> The offline fake classifier is a keyword heuristic, not a real detector — its
> recall/precision here only exercise the harness. Real numbers come from running
> the eval against the Anthropic-backed classifier.
