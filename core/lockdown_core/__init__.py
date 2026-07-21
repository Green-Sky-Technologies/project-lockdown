"""Project Lockdown detection core.

A stateless detection core that classifies chatbot conversation windows and
emits a :class:`Verdict` — the single contract every surface renders from
(design doc §5). See ``technical-design-doc.md`` for the full design.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
