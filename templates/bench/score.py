"""Deterministic outcome scorer.

Score on the REAL outcome the arm produced — never a proxy. The cardinal sin
this guards against: optimising a number that correlates with success instead of
success itself (high recall@k that still gets the task wrong; a faster function
that returns the wrong answer). The value the arm actually produced is the truth.

Four outcomes, deliberately distinct:
  pass          -> the correct outcome
  wrong         -> the case's known-wrong/stale token exactly (the anticipated trap)
  fail          -> some other wrong outcome
  inconclusive  -> nothing actionable (the arm declined / produced no answer)

`wrong` and `fail` are both confident-wrong (corrupting); `wrong` is the strongest
signal — the arm produced *exactly* the value the case flagged as the trap. The
runner treats both as failures for pass-rate, but reports `wrong` separately.

`inconclusive` is NOT a failure: an arm that abstains does less harm than one that
confidently produces a wrong answer. Keeping them separate lets a harm analysis tell
"silent" (abstain) from "corrupting" (wrong/fail).
"""

from __future__ import annotations

_EMPTY = {"", "none", "missing", "unknown", "n/a", "null"}


def classify(output: str, expected: str, wrong: str = "") -> str:
    o = (output or "").strip()
    if o == expected:                 # check the real answer FIRST, so an empty-ish
        return "pass"                 # expected token (e.g. "none", "n/a") still scores pass
    if wrong and o == wrong:
        return "wrong"
    if o.lower() in _EMPTY:
        return "inconclusive"
    return "fail"
