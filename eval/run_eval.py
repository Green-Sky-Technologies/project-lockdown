#!/usr/bin/env python3
"""Standing red-team recall/precision eval (design doc §7, §9).

False negatives are invisible by construction — we only ever see flagged-confirmed
and flagged-cleared; *missed entirely* never enters the funnel. So we generate
misses deliberately: a growing dataset of oblique intent phrased by researchers,
and measure recall against it. This is the honest false-negative estimate, and
the number that matters most for a safety tool.

Runs the SAME classify path the extension hits (reuses ``build_service``), so the
eval measures the real decision, not a re-implementation.

Usage:
    python eval/run_eval.py                       # offline, uses whatever classifier the env wires
    LOCKDOWN_USE_FAKE_CLASSIFIER=1 python eval/run_eval.py   # force the deterministic fake
    LANGSMITH_API_KEY=... LANGSMITH_TRACING=true python eval/run_eval.py --push

``--push`` uploads the dataset to LangSmith (datasets + eval are its real value,
§7); without a key it just prints the local metrics.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Make the core importable when run from the repo root.
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "core"))

from lockdown_core.app import build_service  # noqa: E402
from lockdown_core.contract.actions import crosses_lock_threshold  # noqa: E402
from lockdown_core.contract.verdict import (  # noqa: E402
    CaptureSurface,
    Category,
    ClassifyRequest,
    ClientMetadata,
    Turn,
)
from lockdown_core.settings import Settings  # noqa: E402

DATASET = REPO / "eval" / "datasets" / "redteam_recall.jsonl"


def load_dataset() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]


def _request(text: str) -> ClassifyRequest:
    return ClassifyRequest(
        windowed_text=[Turn(role="user", text=text)],
        category_set=[Category.VIOLENCE_TO_OTHERS],
        client_metadata=ClientMetadata(
            chatbot_host="eval.local",
            capture_surface=CaptureSurface.CHROMIUM_EXT,
            monitored_categories=[Category.VIOLENCE_TO_OTHERS],
        ),
        inline_tier2=True,
    )


async def evaluate() -> dict:
    # No notifications / pipeline during eval.
    service = build_service(Settings(use_langgraph_pipeline=False))
    examples = load_dataset()

    tp = fp = tn = fn = 0
    rows = []
    for ex in examples:
        verdict = await service.classify(_request(ex["text"]))
        flagged = crosses_lock_threshold(verdict.recommended_action)
        should = bool(ex["should_flag"])
        if should and flagged:
            tp += 1
        elif should and not flagged:
            fn += 1
        elif not should and flagged:
            fp += 1
        else:
            tn += 1
        rows.append(
            {
                "should_flag": should,
                "flagged": flagged,
                "directed_at": verdict.directed_at.value,
                "action": verdict.recommended_action.value,
                "text": ex["text"][:70],
            }
        )

    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "recall": recall, "precision": precision, "rows": rows}


def print_report(metrics: dict) -> None:
    print(f"\n{'FLAG?':<6}{'EXPECT':<8}{'directed_at':<24}{'action':<44}text")
    print("-" * 120)
    for r in metrics["rows"]:
        mark = "✓" if r["flagged"] == r["should_flag"] else "✗"
        print(
            f"{mark:<6}{('flag' if r['should_flag'] else 'clear'):<8}"
            f"{r['directed_at']:<24}{r['action']:<44}{r['text']}"
        )
    print("-" * 120)
    print(
        f"recall={metrics['recall']:.2f}  precision={metrics['precision']:.2f}  "
        f"(tp={metrics['tp']} fp={metrics['fp']} tn={metrics['tn']} fn={metrics['fn']})"
    )
    print(
        "\nRecall is the headline number for a safety tool (missed threats). "
        "Grow redteam_recall.jsonl over time — this is our honest false-negative estimate.\n"
    )


def push_to_langsmith() -> None:
    """Upload the dataset to LangSmith so its datasets + eval tooling can track it."""
    if not os.getenv("LANGSMITH_API_KEY"):
        print("LANGSMITH_API_KEY not set — skipping --push.")
        return
    try:
        from langsmith import Client
    except ImportError:
        print("langsmith not installed — skipping --push.")
        return

    client = Client()
    name = "project-lockdown-redteam-recall"
    examples = load_dataset()
    dataset = client.create_dataset(dataset_name=name, description="Design doc §7/§9 standing red-team recall set.")
    client.create_examples(
        inputs=[{"text": e["text"]} for e in examples],
        outputs=[{"should_flag": e["should_flag"], "expected_directed_at": e["expected_directed_at"]} for e in examples],
        dataset_id=dataset.id,
    )
    print(f"Uploaded {len(examples)} examples to LangSmith dataset '{name}'.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--push", action="store_true", help="upload the dataset to LangSmith")
    args = parser.parse_args()

    metrics = asyncio.run(evaluate())
    print_report(metrics)
    if args.push:
        push_to_langsmith()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
