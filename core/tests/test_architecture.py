"""Architecture guard: LangGraph must never touch the classifier hot path.

Design doc §4.3 requires ``/classify`` to be a thin, stateless SDK call — "fewer
layers between input and 'lock a kid out'". We enforce it by importing the hot
path in a *fresh* interpreter and asserting ``langgraph`` never got imported.
"""

import subprocess
import sys

# Modules that constitute the hot path. Importing these must not pull in langgraph.
HOT_PATH_MODULES = [
    "lockdown_core.classify.service",
    "lockdown_core.classify.types",
    "lockdown_core.contract.actions",
    "lockdown_core.contract.verdict",
]


def test_langgraph_absent_from_hot_path():
    script = (
        "import sys;"
        + "".join(f"__import__('{m}');" for m in HOT_PATH_MODULES)
        + "bad=[m for m in sys.modules if m=='langgraph' or m.startswith('langgraph.')];"
        + "print('LEAK:'+','.join(bad)) if bad else print('CLEAN');"
        + "sys.exit(1 if bad else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"langgraph leaked onto the hot path: {result.stdout}{result.stderr}"
    assert "CLEAN" in result.stdout


def test_pipeline_seam_is_langgraph_free():
    """The service depends on pipeline.base (the Protocol seam), which must not
    import langgraph. The concrete LangGraph runner lives in pipeline.graph and is
    only reached from the composition root."""
    script = (
        "import sys;"
        "__import__('lockdown_core.pipeline.base');"
        "bad=[m for m in sys.modules if m=='langgraph' or m.startswith('langgraph.')];"
        "sys.exit(1 if bad else 0)"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, f"langgraph leaked via pipeline.base seam: {result.stderr}"


def test_langgraph_pipeline_does_import_langgraph():
    """Positive control: the concrete pipeline SHOULD pull in langgraph — that is
    where the graph legitimately lives."""
    script = (
        "import sys;"
        "__import__('lockdown_core.pipeline.graph');"
        "ok=any(m=='langgraph' or m.startswith('langgraph.') for m in sys.modules);"
        "sys.exit(0 if ok else 1)"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, "pipeline.graph unexpectedly did not import langgraph"
