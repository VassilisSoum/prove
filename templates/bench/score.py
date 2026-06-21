"""Deterministic outcome scorer.

Score on the REAL outcome the arm produced — never a proxy. The cardinal sin
this guards against: optimising a number that correlates with success instead of
success itself (high recall@k that still gets the task wrong; a faster function
that returns the wrong answer). The value the arm actually produced is the truth.

Three outcomes, deliberately distinct:
  pass          -> the correct outcome
  fail          -> a wrong outcome (incl. the known-wrong/stale token)
  inconclusive  -> nothing actionable (the arm declined / produced no answer)

`inconclusive` is NOT `fail`: an arm that abstains is doing less harm than an arm
that confidently produces a wrong answer. Keep them separate so a harm analysis
can tell "silent" from "corrupting".
"""

from __future__ import annotations

_EMPTY = {"", "none", "missing", "unknown", "n/a", "null"}


def classify(output: str, expected: str, wrong: str = "") -> str:
    o = (output or "").strip()
    if o.lower() in _EMPTY:
        return "inconclusive"
    if o == expected:
        return "pass"
    return "fail"
