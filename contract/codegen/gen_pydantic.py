#!/usr/bin/env python3
"""Generate a *reference* Pydantic model from the verdict schema.

The committed mirror at ``core/lockdown_core/contract/verdict.py`` is
hand-maintained (it carries docstrings, a strict base class, and the
``ClassifyRequest`` types drawn from a second schema) — so we do NOT text-diff
against a generator. Instead this script emits a reference model you can eyeball
when changing the schema, and the real drift guard is the schema-parity test at
``core/tests/test_contract_parity.py`` (it validates the committed model's output
against ``verdict.schema.json`` and compares enum sets).

    python contract/codegen/gen_pydantic.py            # -> contract/codegen/_generated/verdict_ref.py

Requires the ``dev`` extra: ``uv pip install -e 'core[dev]'``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCHEMA = REPO / "contract" / "verdict.schema.json"
OUT = REPO / "contract" / "codegen" / "_generated" / "verdict_ref.py"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            str(SCHEMA),
            "--input-file-type",
            "jsonschema",
            "--output",
            str(OUT),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-standard-collections",
            "--use-union-operator",
            "--field-constraints",
        ],
        check=True,
    )
    print(f"wrote reference model {OUT.relative_to(REPO)}")
    print("The committed mirror is core/lockdown_core/contract/verdict.py;")
    print("parity is enforced by core/tests/test_contract_parity.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
