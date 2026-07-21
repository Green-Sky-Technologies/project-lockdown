"""The classifier hot path (design doc §4.3).

A thin, stateless ``text in → verdict out`` critical path. Deliberately NOT a
graph — legibility over machinery for a tool that can lock a kid out. LangGraph
lives only on the async pipeline (``lockdown_core.pipeline``); an architecture
test asserts it never appears on this import path.
"""
