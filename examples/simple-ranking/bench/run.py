#!/usr/bin/env python3
"""Trials runner — the harness core.

Runs each arm over every case N times, scores each output, aggregates, computes
lift vs the floor baseline, writes a result JSON to results/, and appends a row to
EXPERIMENTS.md.

Two kinds of case (see registry.py):
  - outcome (default): the arm returns a token, scored pass/wrong/fail/inconclusive
    against the case's expected (and optional known-wrong) value.
  - numeric: the arm returns a number; the runner reports median/mean/p95 and a
    bootstrap confidence interval of (candidate - floor) to test "beyond noise".

What this encodes, mechanically, so you cannot skip it:
  - equal budget   : every arm sees the same cases
  - real outcome   : outcome scoring goes through score.classify (no proxy metric)
  - trials         : --trials N runs each (arm, case) N times to separate signal from
                     noise; a numeric metric needs trials>=2 to establish a noise band
  - floor baseline : lift / improvement is always reported against the `floor` arm
  - durable record : results/<ts>.json + an EXPERIMENTS.md row, ALWAYS

Usage:
  python run.py [--arms a,b,c] [--trials N] [--hypothesis "..."] [--lever "..."]
                [--verbose] [--fail-on REVERT,REVIEW]

Verdict (KEEP / REVIEW / REVERT): a candidate ships ONLY if it beats the floor beyond
noise without introducing a corrupting regression. Otherwise REVIEW or REVERT — and the
ledger keeps the result so the same idea is not re-tried on faith later.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import registry as reg  # noqa: E402
import score as sc      # noqa: E402

_BOOTSTRAP_ITERS = 1000
_BOOTSTRAP_SEED = 12345   # fixed so a run is reproducible (and CI/examples are stable)


def _percentile(xs, p):
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round((p / 100.0) * (len(xs) - 1)))))
    return xs[k]


def _bootstrap_ci_diff(floor_vals, cand_vals, direction):
    """95% CI of the IMPROVEMENT of cand over floor (positive = cand better).
    For direction 'lower', improvement = floor_median - cand_median; for 'higher',
    cand_median - floor_median. Stdlib only; seeded for reproducibility."""
    rng = random.Random(_BOOTSTRAP_SEED)
    diffs = []
    for _ in range(_BOOTSTRAP_ITERS):
        fm = statistics.median(rng.choices(floor_vals, k=len(floor_vals)))
        cm = statistics.median(rng.choices(cand_vals, k=len(cand_vals)))
        diffs.append((fm - cm) if direction == "lower" else (cm - fm))
    diffs.sort()
    lo = diffs[int(round(0.025 * (len(diffs) - 1)))]
    hi = diffs[int(round(0.975 * (len(diffs) - 1)))]
    return lo, hi


def aggregate(cells, arms, floor, meta, trials):
    """Pure scoring/verdict logic — no IO, so it is unit-testable.

    cells: {(arm, case_id): [outcome_str | float, ...]}  (outcome cells hold classified
           tokens; numeric cells hold floats)
    meta:  ordered {case_id: {"kind": "outcome"} | {"kind": "numeric", "direction": ...}}
    Returns the full result record dict (verdict, decision, cautions, per-case, ...).
    """
    case_ids = list(meta.keys())
    n_cases = len(case_ids)
    outcome_ids = [c for c in case_ids if meta[c]["kind"] == "outcome"]
    numeric_ids = [c for c in case_ids if meta[c]["kind"] == "numeric"]

    # ---- outcome tally (over outcome cells only) ----
    tally = {a: {"pass": 0, "wrong": 0, "fail": 0, "inconclusive": 0, "n": 0} for a in arms}
    for cid in outcome_ids:
        for a in arms:
            for o in cells[(a, cid)]:
                tally[a][o] += 1
                tally[a]["n"] += 1
    agg = {a: {**tally[a], "pass_rate": (tally[a]["pass"] / tally[a]["n"]) if tally[a]["n"] else 0.0}
           for a in arms}

    def _cw_rate(n):
        x = agg[n]
        return ((x["wrong"] + x["fail"]) / x["n"]) if x["n"] else 0.0

    # ---- numeric stats per (numeric case, arm) ----
    numeric = {}
    for cid in numeric_ids:
        numeric[cid] = {}
        for a in arms:
            vals = [float(v) for v in cells[(a, cid)]]
            numeric[cid][a] = {"median": statistics.median(vals),
                               "mean": statistics.fmean(vals),
                               "p95": _percentile(vals, 95), "n": len(vals)}

    def _num_improvement(n):
        """Average relative improvement of arm n vs floor over numeric cases (+ = better)."""
        if not numeric_ids or floor is None or n == floor:
            return 0.0
        rels = []
        for cid in numeric_ids:
            d = meta[cid].get("direction", "lower")
            fm, nm = numeric[cid][floor]["median"], numeric[cid][n]["median"]
            rels.append(0.0 if fm == 0 else (((fm - nm) / abs(fm)) if d == "lower" else ((nm - fm) / abs(fm))))
        return sum(rels) / len(rels)

    candidates = [n for n in arms if n != floor]
    # Rank by outcome pass-rate, then fewest confident-wrong, then numeric improvement.
    best = max(candidates, key=lambda n: (agg[n]["pass_rate"], -_cw_rate(n), _num_improvement(n))) \
        if candidates else floor
    floor_rate = agg[floor]["pass_rate"] if floor else 0.0
    best_lift = agg[best]["pass_rate"] - floor_rate

    # ---- numeric noise-band test for best vs floor ----
    numeric_findings = []
    numeric_improves = bool(numeric_ids)
    numeric_regresses = False
    numeric_underpowered = bool(numeric_ids) and trials < 2
    if numeric_ids and floor is not None and best != floor:
        for cid in numeric_ids:
            d = meta[cid].get("direction", "lower")
            fm, bm = numeric[cid][floor]["median"], numeric[cid][best]["median"]
            improve = 0.0 if fm == 0 else (((fm - bm) / abs(fm)) if d == "lower" else ((bm - fm) / abs(fm)))
            if trials < 2:                         # no samples to bootstrap a noise band
                lo, hi, v = 0.0, 0.0, "within-noise"
            else:
                lo, hi = _bootstrap_ci_diff([float(x) for x in cells[(floor, cid)]],
                                            [float(x) for x in cells[(best, cid)]], d)
                v = "better" if lo > 0 else "worse" if hi < 0 else "within-noise"
            if v != "better":
                numeric_improves = False
            if v == "worse":
                numeric_regresses = True
            numeric_findings.append({"case": cid, "direction": d, "floor_median": fm,
                                     "best_median": bm, "improve_pct": improve,
                                     "ci": [lo, hi], "verdict": v})

    # ---- honesty cautions ----
    deterministic = all(len(set(cells[k])) == 1 for k in cells)
    cautions = []
    if floor is None:
        cautions.append("No floor baseline — lift is meaningless. Add an arm with is_floor=True.")
    if trials > 1 and deterministic:
        cautions.append(
            f"Metric is DETERMINISTIC — all {trials} trials of every cell were identical. Trials "
            f"added no information: effective n = {n_cases} cases, NOT {trials * n_cases}. Raising "
            f"--trials cannot strengthen this; adding cases can.")
    if n_cases < 10:
        cautions.append(
            f"Small case set (n={n_cases}). A lift here is SUGGESTIVE, not decisive. Add cases — "
            f"especially ADVERSARIAL ones that probe where the candidate should FAIL, not only "
            f"where it should win.")
    floor_cw = _cw_rate(floor) if floor else 0.0
    best_cw = _cw_rate(best)
    corrupting = best != floor and best_cw > floor_cw
    if corrupting:
        cautions.append(
            f"Candidate '{best}' introduces confident-WRONG outcomes the floor did not have "
            f"(wrong/fail rate {best_cw:.0%} vs floor {floor_cw:.0%}). A wrong answer is worse "
            f"than an abstention — a higher pass-rate bought with corrupting errors is not a win.")
    if numeric_underpowered:
        cautions.append(
            "Numeric metric ran with trials<2 — no noise band could be estimated, so the change "
            "is treated as within-noise. Raise --trials to establish significance.")
    if numeric_regresses:
        cautions.append(f"Candidate '{best}' REGRESSES a numeric metric beyond noise vs the floor.")
    if numeric_ids and best != floor and not numeric_improves and not numeric_regresses and not numeric_underpowered:
        cautions.append(
            f"Numeric change is WITHIN run-to-run noise (bootstrap CI of the floor-vs-{best} "
            "difference straddles 0) — not a measured improvement.")

    # ---- verdict (outcome component + numeric component, combined) ----
    has_outcome, has_numeric = bool(outcome_ids), bool(numeric_ids)
    ov = None
    if has_outcome:
        ov = "REVERT" if (best == floor or best_lift <= 0) else "REVIEW" if corrupting else "KEEP"
    nv = None
    if has_numeric and best != floor:
        nv = "REVERT" if numeric_regresses else "KEEP" if numeric_improves else "REVIEW"
    comps = [v for v in (ov, nv) if v]

    if best == floor or not comps:
        verdict = "REVERT"
    elif "KEEP" in comps and ("REVERT" in comps or "REVIEW" in comps):
        verdict = "REVIEW"
    elif all(v == "KEEP" for v in comps):
        verdict = "KEEP"
    elif "KEEP" not in comps and "REVIEW" not in comps:
        verdict = "REVERT"
    else:
        verdict = "REVIEW"

    if verdict == "KEEP":
        decision = "KEEP — measured benefit"
    elif verdict == "REVERT":
        decision = "REVERT — no measured benefit"
    elif corrupting and ov == "REVIEW" and "KEEP" not in comps:
        decision = "REVIEW — coverage up, but introduces corrupting failures the floor avoided"
    elif "KEEP" in comps:
        decision = "REVIEW — improves one axis but regresses or is inconclusive on another"
    else:
        decision = "REVIEW — change is within run-to-run noise (not a measured benefit)"

    # ---- per-case detail ----
    per_case = []
    for cid in case_ids:
        row = {"case": cid, "kind": meta[cid]["kind"], "arms": {}}
        for a in arms:
            vals = cells[(a, cid)]
            if meta[cid]["kind"] == "numeric":
                row["arms"][a] = round(numeric[cid][a]["median"], 4)
            else:
                uniq = sorted(set(vals))
                row["arms"][a] = uniq[0] if len(uniq) == 1 else f"mixed{uniq}"
        per_case.append(row)

    if has_outcome:
        headline = f"{best} {agg[best]['pass_rate']:.0%} (lift {best_lift:+.0%})"
    else:
        headline = f"{best} ({_num_improvement(best):+.0%} vs floor on {len(numeric_ids)} numeric case(s))"

    return {
        "trials": trials, "cases": n_cases,
        "effective_n": n_cases if deterministic else trials * n_cases,
        "deterministic": deterministic, "floor": floor,
        "arms": agg, "numeric": numeric, "numeric_findings": numeric_findings,
        "best": best, "best_lift": best_lift,
        "verdict": verdict, "decision": decision, "headline": headline,
        "cautions": cautions, "per_case": per_case,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=",".join(reg.ARMS),
                    help="comma list of arms to run (default: all registered)")
    ap.add_argument("--trials", type=int, default=5,
                    help="repeats per (arm, case) — raise this for a noisy/numeric metric")
    ap.add_argument("--hypothesis", default="", help="the claim under test")
    ap.add_argument("--lever", default="", help="the ONE thing that differs between arms")
    ap.add_argument("--verbose", action="store_true", help="print a per-case x arm table")
    ap.add_argument("--fail-on", default="",
                    help="comma verdicts (e.g. REVERT,REVIEW) that make this exit non-zero (CI gate)")
    args = ap.parse_args()

    arms = [a.strip() for a in args.arms.split(",") if a.strip() in reg.ARMS]
    unknown = [a.strip() for a in args.arms.split(",") if a.strip() and a.strip() not in reg.ARMS]
    if unknown:
        print(f"unknown arm(s) ignored: {', '.join(unknown)} (available: {', '.join(reg.ARMS)})",
              file=sys.stderr)
    if not arms:
        print("no valid arms selected.", file=sys.stderr)
        return 2
    if hasattr(reg, "validate"):
        reg.validate(arms)   # raises with a clear message on a malformed experiment

    floor = next((n for n in arms if reg.ARMS[n].is_floor), None)

    cells, meta = {}, {}
    for case in reg.CASES:
        kind = getattr(case, "kind", "outcome")
        for name in arms:
            raw = [reg.ARMS[name].run(case) for _ in range(args.trials)]
            cells[(name, case.id)] = ([float(v) for v in raw] if kind == "numeric"
                                      else [sc.classify(v, case.expected, case.wrong) for v in raw])
        meta[case.id] = ({"kind": "numeric", "direction": getattr(case, "direction", "lower"),
                          "label": getattr(case, "label", case.id)} if kind == "numeric"
                         else {"kind": "outcome"})

    record = aggregate(cells, arms, floor, meta, args.trials)

    _now = datetime.now(timezone.utc)
    ts = _now.strftime("%Y%m%dT%H%M%S") + f"_{_now.microsecond // 1000:03d}Z"
    record = {"ts": ts, "hypothesis": args.hypothesis, "lever": args.lever, **record}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", f"{ts}.json"), "w") as f:
        json.dump(record, f, indent=2)

    _print_report(record, arms, floor, meta, args.verbose)

    appended = _append_ledger(record)
    tail = "  and a row in EXPERIMENTS.md" if appended else "  (no EXPERIMENTS.md found — ledger row skipped)"
    print(f"recorded -> results/{ts}.json{tail}")

    fail_on = {v.strip().upper() for v in args.fail_on.split(",") if v.strip()}
    if record["verdict"] in fail_on:
        print(f"\n--fail-on: verdict {record['verdict']} is in {sorted(fail_on)} -> exit 1", file=sys.stderr)
        return 1
    return 0


def _print_report(record, arms, floor, meta, verbose):
    agg, numeric, floor_rate = record["arms"], record["numeric"], (record["arms"][floor]["pass_rate"] if floor else 0.0)
    outcome_ids = [c for c in meta if meta[c]["kind"] == "outcome"]
    numeric_ids = [c for c in meta if meta[c]["kind"] == "numeric"]
    print(f"\n=== experiment {record['ts']}  (trials={record['trials']}/arm, cases={record['cases']}) ===")
    if record["hypothesis"]:
        print(f"hypothesis: {record['hypothesis']}")
    if record["lever"]:
        print(f"lever:      {record['lever']}")
    if outcome_ids:
        for name in arms:
            a = agg[name]
            tag = "  (floor)" if name == floor else f"   lift {a['pass_rate'] - floor_rate:+.0%}"
            print(f"  {name:16s} pass {a['pass']:>3}/{a['n']:<3} ({a['pass_rate']:>4.0%})"
                  f"  wrong {a['wrong']:>3}  fail {a['fail']:>3}  inconcl {a['inconclusive']:>3}{tag}")
    for f in record["numeric_findings"]:
        ci = f["ci"]
        print(f"  numeric[{f['case']}] floor median {f['floor_median']:.4g} -> {record['best']} "
              f"{f['best_median']:.4g}  ({f['improve_pct']:+.0%}, {f['verdict']}; "
              f"95% CI diff [{ci[0]:.4g}, {ci[1]:.4g}])")
    print(f"\nverdict: {record['decision']}  (best candidate: {record['best']})")
    if verbose:
        print("\nper-case:")
        for row in record["per_case"]:
            cells_str = "  ".join(f"{a}={row['arms'][a]}" for a in arms)
            print(f"  [{row['kind'][:3]}] {row['case']:18s} {cells_str}")
    if record["cautions"]:
        print("\ncautions (the verdict above is only as trustworthy as these allow):")
        for c in record["cautions"]:
            print(f"  ⚠ {c}")


def _append_ledger(record: dict) -> bool:
    led = os.path.join(HERE, "EXPERIMENTS.md")
    if not os.path.exists(led):
        return False
    decision = record["decision"]
    if record.get("cautions"):
        decision += f" ⚠×{len(record['cautions'])} (see results/{record['ts']}.json)"
    row = (f"| {record['ts']} "
           f"| {record['hypothesis'] or '—'} "
           f"| {record['lever'] or '—'} "
           f"| {record['trials']} "
           f"| {record['headline']} "
           f"| {decision} |\n")
    with open(led, "a") as f:
        f.write(row)
    return True


if __name__ == "__main__":
    raise SystemExit(main())
