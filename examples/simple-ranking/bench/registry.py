"""Experiment: should we ship candidate_rank instead of baseline_rank?

LEVER (the one thing that differs): the ranking function.
  floor     = ranking.baseline_rank   (current: exact keyword overlap, abstains on no match)
  candidate = ranking.candidate_rank  (proposed: + substring matching, never abstains)

EQUAL BUDGET: both arms see the same queries. A None return maps to "" so it scores
`inconclusive` (a safe abstention), kept distinct from a confidently-wrong doc
(`wrong`/`fail`). REAL OUTCOME: the top doc returned == the documented-correct doc.

The cases are chosen to show all the outcomes that matter:
  * GROUP A — both rank correctly (pass / pass)
  * GROUP B — query uses a word VARIANT ("migrations", "refunding"): the floor abstains
              (inconclusive, safe) and the candidate's substring matching wins (pass) —
              the candidate's genuine improvement
  * GROUP C — ADVERSARIAL junk the corpus can't answer: the floor abstains (correct!),
              the candidate hallucinates a match via a spurious substring (redis ⊂
              "redistribute") and returns a confidently WRONG doc

So the candidate gains coverage on B but introduces a corrupting error on C. That is
exactly the trade-off pass-rate alone hides — watch the `wrong` column and the verdict.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # example root
import ranking  # noqa: E402  (the code under test)


@dataclass
class Case:
    id: str
    payload: dict = field(default_factory=dict)
    expected: str = ""
    wrong: str = ""


@dataclass
class Arm:
    name: str
    run: Callable[[Case], str]
    is_floor: bool = False


ARMS: dict[str, Arm] = {}


def register(arm: Arm) -> Arm:
    if arm.name in ARMS:
        raise ValueError(f"duplicate arm name {arm.name!r} — each arm needs a unique name")
    ARMS[arm.name] = arm
    return arm


CASES: list[Case] = [
    # GROUP A — both should rank correctly
    Case(id="reset",   payload={"q": "reset my password"},            expected="auth/reset.md"),
    Case(id="refund",  payload={"q": "issue a refund for this charge"}, expected="billing/refund.md"),
    Case(id="login",   payload={"q": "i forgot my login"},            expected="auth/reset.md"),

    # GROUP B — word variants: floor abstains (inconclusive), candidate wins (pass)
    Case(id="migrate", payload={"q": "perform db migrations"},        expected="db/migrate.md"),
    Case(id="refunding", payload={"q": "refunding the customer"},     expected="billing/refund.md"),

    # GROUP C — adversarial junk: correct behaviour is to ABSTAIN (expected "").
    # candidate hallucinates: "redis" is a substring of "redistribute" -> cache/ttl.md
    Case(id="junk",    payload={"q": "redistribute traffic"},         expected="", wrong="cache/ttl.md"),
]

register(Arm(name="baseline", is_floor=True,                                   # current production
             run=lambda c: ranking.baseline_rank(c.payload["q"]) or ""))
register(Arm(name="candidate",                                                 # the proposed change
             run=lambda c: ranking.candidate_rank(c.payload["q"]) or ""))
