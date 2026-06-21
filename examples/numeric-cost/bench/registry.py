"""Experiment: should we ship count_setbased instead of count_naive?

LEVER: the membership-check implementation.
  floor     = cost.count_naive      (rescans the list per query)
  candidate = cost.count_setbased   (builds a set once, O(1) lookups)

NUMERIC metric: number of element comparisons (direction="lower" — fewer is better).
The metric is exact/deterministic, so the result is reproducible; the bootstrap CI of
(candidate - floor) confirms the improvement is beyond noise rather than a lucky run.

EQUAL BUDGET: both arms get the identical workload (same items + same queries) per case.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # example root
import cost  # noqa: E402  (the code under test)


@dataclass
class Case:
    id: str
    payload: dict = field(default_factory=dict)
    expected: str = ""
    wrong: str = ""
    kind: str = "outcome"
    direction: str = "lower"
    label: str = ""


@dataclass
class Arm:
    name: str
    run: Callable[[Case], object]
    is_floor: bool = False


ARMS: dict[str, Arm] = {}


def register(arm: Arm) -> Arm:
    if arm.name in ARMS:
        raise ValueError(f"duplicate arm name {arm.name!r} — each arm needs a unique name")
    ARMS[arm.name] = arm
    return arm


def validate(arms=None) -> None:
    arms = list(ARMS) if arms is None else arms
    floors = [n for n in arms if ARMS[n].is_floor]
    if len(floors) != 1:
        raise ValueError(f"expected exactly one floor arm, found {len(floors)}: {floors}")


def _comparisons(fn, case):
    items, targets = cost.make_workload(case.payload["n"], case.payload["present"])
    return float(fn(items, targets))


CASES: list[Case] = [
    Case(id="present_500",  payload={"n": 500,  "present": True},  kind="numeric",
         direction="lower", label="comparisons"),
    Case(id="present_2000", payload={"n": 2000, "present": True},  kind="numeric",
         direction="lower", label="comparisons"),
    Case(id="absent_1000",  payload={"n": 1000, "present": False}, kind="numeric",
         direction="lower", label="comparisons"),
]

register(Arm(name="naive", is_floor=True,                              # current production
             run=lambda c: _comparisons(cost.count_naive, c)))
register(Arm(name="setbased",                                          # the proposed change
             run=lambda c: _comparisons(cost.count_setbased, c)))
