#!/usr/bin/env python3
"""Trials runner — the harness core.

Runs each arm over every case N times, scores each output on the real outcome,
aggregates pass-rate per arm, computes lift vs the floor baseline, writes a
result JSON to results/, and appends a row to EXPERIMENTS.md.

What this encodes, mechanically, so you cannot skip it:
  - equal budget   : every arm sees the same cases
  - real outcome   : scoring goes through score.classify (no proxy metric)
  - trials         : --trials N runs each (arm, case) N times to separate signal
                     from run-to-run noise; a 1-trial "win" on a noisy metric is
                     not a win
  - floor baseline : lift is always reported against the `floor` arm
  - durable record : results/<ts>.json + an EXPERIMENTS.md row, ALWAYS — a
                     no-benefit result is recorded too, then you revert

Usage:
  python run.py [--arms a,b,c] [--trials N] [--hypothesis "..."] [--lever "..."]

Decision rule (printed at the end): a candidate ships ONLY if it beats the floor
beyond noise. Otherwise the verdict is REVERT — and the ledger keeps the negative
result so the same idea is not re-tried on faith later.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import registry as reg  # noqa: E402
import score as sc      # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=",".join(reg.ARMS),
                    help="comma list of arms to run (default: all registered)")
    ap.add_argument("--trials", type=int, default=5,
                    help="repeats per (arm, case) — raise this for a noisy metric")
    ap.add_argument("--hypothesis", default="", help="the claim under test")
    ap.add_argument("--lever", default="", help="the ONE thing that differs between arms")
    args = ap.parse_args()

    arms = [a.strip() for a in args.arms.split(",") if a.strip() in reg.ARMS]
    unknown = [a.strip() for a in args.arms.split(",") if a.strip() and a.strip() not in reg.ARMS]
    if unknown:
        print(f"unknown arm(s) ignored: {', '.join(unknown)} "
              f"(available: {', '.join(reg.ARMS)})", file=sys.stderr)
    if not arms:
        print("no valid arms selected.", file=sys.stderr)
        return 2

    floor = next((n for n in arms if reg.ARMS[n].is_floor), None)

    # Run every (arm, case) CELL `--trials` times, keeping the per-cell outcomes —
    # so we can tell a real (stochastic) sample from a deterministic one repeated N
    # times, and not flatter the result with a fake sample size.
    cells: dict[tuple[str, str], list[str]] = {}
    for case in reg.CASES:
        for name in arms:
            arm = reg.ARMS[name]
            cells[(name, case.id)] = [
                sc.classify(arm.run(case), case.expected, case.wrong)
                for _ in range(args.trials)
            ]

    tally = {a: {"pass": 0, "fail": 0, "inconclusive": 0, "n": 0} for a in arms}
    for (name, _cid), outs in cells.items():
        for o in outs:
            tally[name][o] += 1
            tally[name]["n"] += 1

    agg = {n: {**tally[n], "pass_rate": (tally[n]["pass"] / tally[n]["n"]) if tally[n]["n"] else 0.0}
           for n in arms}
    floor_rate = agg[floor]["pass_rate"] if floor else 0.0

    # --- honesty checks: refuse to let the harness flatter a weak experiment -----
    n_cases = len(reg.CASES)
    deterministic = all(len(set(outs)) == 1 for outs in cells.values())
    cautions: list[str] = []
    if floor is None:
        cautions.append("No floor baseline — lift is meaningless. Add an arm with is_floor=True.")
    if args.trials > 1 and deterministic:
        cautions.append(
            f"Metric is DETERMINISTIC — all {args.trials} trials of every cell were identical. "
            f"Trials added no information: effective n = {n_cases} cases, NOT "
            f"{args.trials * n_cases}. Raising --trials cannot strengthen this; adding cases can.")
    if n_cases < 10:
        cautions.append(
            f"Small case set (n={n_cases}). A lift here is SUGGESTIVE, not decisive. Add cases — "
            f"especially ADVERSARIAL ones that probe where the candidate should FAIL, not only "
            f"where it should win.")

    # millisecond precision so two runs in the same second don't clobber each other's JSON
    _now = datetime.now(timezone.utc)
    ts = _now.strftime("%Y%m%dT%H%M%S") + f"_{_now.microsecond // 1000:03d}Z"
    candidates = [n for n in arms if n != floor]
    best = max(candidates, key=lambda n: agg[n]["pass_rate"]) if candidates else floor
    best_lift = agg[best]["pass_rate"] - floor_rate
    decision = "KEEP — measured benefit" if (best != floor and best_lift > 0) else "REVERT — no measured benefit"

    record = {
        "ts": ts, "hypothesis": args.hypothesis, "lever": args.lever,
        "trials": args.trials, "cases": n_cases,
        "effective_n": n_cases if deterministic else args.trials * n_cases,
        "deterministic": deterministic, "floor": floor,
        "arms": agg, "best": best, "best_lift": best_lift, "decision": decision,
        "cautions": cautions,
    }
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", f"{ts}.json"), "w") as f:
        json.dump(record, f, indent=2)

    print(f"\n=== experiment {ts}  (trials={args.trials}/arm, cases={len(reg.CASES)}) ===")
    if args.hypothesis:
        print(f"hypothesis: {args.hypothesis}")
    if args.lever:
        print(f"lever:      {args.lever}")
    for name in arms:
        a = agg[name]
        tag = "  (floor)" if name == floor else f"   lift {a['pass_rate'] - floor_rate:+.0%}"
        print(f"  {name:16s} pass {a['pass']:>3}/{a['n']:<3} ({a['pass_rate']:>4.0%})"
              f"  fail {a['fail']:>3}  inconcl {a['inconclusive']:>3}{tag}")
    print(f"\nverdict: {decision}  (best candidate: {best}, lift {best_lift:+.0%})")
    if cautions:
        print("\ncautions (the verdict above is only as trustworthy as these allow):")
        for c in cautions:
            print(f"  ⚠ {c}")

    _append_ledger(record)
    print(f"recorded -> results/{ts}.json  and a row in EXPERIMENTS.md")
    return 0


def _append_ledger(record: dict) -> None:
    led = os.path.join(HERE, "EXPERIMENTS.md")
    if not os.path.exists(led):
        return
    agg = record["arms"]
    best = record["best"]
    # A caveated result must not read as a clean verdict in the ledger.
    decision = record["decision"]
    if record.get("cautions"):
        decision += f" ⚠×{len(record['cautions'])} (see results/{record['ts']}.json)"
    row = (f"| {record['ts']} "
           f"| {record['hypothesis'] or '—'} "
           f"| {record['lever'] or '—'} "
           f"| {record['trials']} "
           f"| {best} {agg[best]['pass_rate']:.0%} (lift {record['best_lift']:+.0%}) "
           f"| {decision} |\n")
    with open(led, "a") as f:
        f.write(row)


if __name__ == "__main__":
    raise SystemExit(main())
