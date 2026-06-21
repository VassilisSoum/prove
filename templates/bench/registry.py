"""Arm registry for the empirical benchmark harness.

An *arm* is one approach you are comparing. The harness compares arms over a set
of *cases* and scores each arm on the REAL outcome it produced (see score.py).

Three rules this file exists to enforce:

  1. FLOOR BASELINE. Every experiment includes a `floor` arm — the do-nothing /
     trivial approach. A candidate's worth is its lift *over the floor*, never an
     absolute number against a strawman.

  2. EQUAL BUDGET. Every arm sees the SAME cases with the SAME inputs and the
     SAME resource limits. The only thing that may differ between two arms is the
     ONE lever you are testing. If you change two things at once, you cannot
     attribute the result to either.

  3. ONE LEVER. An experiment isolates a single variable. Want to test two? Run
     two experiments.

Replace the DEMO arms + cases below with your project's real ones. run.py and
score.py never change — they are the harness; this file is your experiment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Case:
    """One scored situation. `payload` is whatever an arm needs to produce its
    output; `expected` is the correct outcome token; `wrong` is an optional
    known-wrong/stale token that sharpens scoring."""
    id: str
    payload: dict = field(default_factory=dict)
    expected: str = ""
    wrong: str = ""


@dataclass
class Arm:
    """One approach under test. `run(case) -> str` produces the value to be
    scored. Mark exactly one arm `is_floor=True`."""
    name: str
    run: Callable[[Case], str]
    is_floor: bool = False


ARMS: dict[str, Arm] = {}


def register(arm: Arm) -> Arm:
    if arm.name in ARMS:
        raise ValueError(f"duplicate arm name {arm.name!r} — each arm needs a unique name")
    ARMS[arm.name] = arm
    return arm


# ============================================================================
# DEMO experiment — DELETE THIS BLOCK and define your own arms + CASES.
#
# Toy "what is the current value?" task. Each case carries a history of values
# that changed over time. The candidate arm reads the latest; the floor arm
# naively takes the first (stale). It's a toy "what is the current value?"
# question — but the harness does not care what the domain is.
#
# When you write your OWN cases, don't only include ones the candidate should win:
# add ADVERSARIAL cases that probe where it should FAIL (that's where regressions
# hide), keep the floor HONEST (no rigged fallback), and prefer cases drawn from
# real usage over ones you hand-pick to favour your change. See bench/README.md
# "Don't fool yourself".
# ============================================================================

CASES: list[Case] = [
    Case(id="ttl",     payload={"history": [300, 600, 900]}, expected="900", wrong="300"),
    Case(id="retries", payload={"history": [3, 5]},          expected="5",   wrong="3"),
    Case(id="workers", payload={"history": [2, 4, 8, 16]},   expected="16",  wrong="2"),
]

register(Arm(
    name="floor",
    is_floor=True,
    run=lambda c: str(c.payload["history"][0]),     # stale: first value ever seen
))

register(Arm(
    name="latest",
    run=lambda c: str(c.payload["history"][-1]),    # candidate: most recent value
))
