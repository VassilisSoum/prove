#!/usr/bin/env python3
"""Turn a Prove results JSON into a PROVE REPORT block for a PR comment.

Usage:
  python scripts/pr_summary.py path/to/bench/results/<ts>.json

The harness gives you the numbers and the verdict; this just formats them. Paste the
output into the PR (or post it from CI).
"""

from __future__ import annotations

import json
import sys


def summarize(rec: dict) -> str:
    lines = ["PROVE REPORT",
             f"Question: {rec.get('hypothesis') or '(no hypothesis recorded)'}",
             f"Verdict:  {rec.get('verdict', '?')}"]
    decision = rec.get("decision", "")
    reason = decision.split("—", 1)[-1].strip() if "—" in decision else decision
    lines.append(f"Reason:   {reason or '(see results JSON)'}")

    best = rec.get("best")
    arms = rec.get("arms", {})
    if best in arms and arms[best].get("n"):
        a = arms[best]
        lines.append(f"Evidence: best={best} pass {a['pass']}/{a['n']} ({a['pass_rate']:.0%}), "
                     f"lift {rec.get('best_lift', 0.0):+.0%} vs floor; "
                     f"trials={rec.get('trials')}, cases={rec.get('cases')}")
    for nf in rec.get("numeric_findings", []):
        lines.append(f"Evidence: {nf['case']} {nf['improve_pct']:+.0%} ({nf['verdict']}) vs floor")
    if rec.get("cautions"):
        lines.append(f"Cautions: {len(rec['cautions'])} — see results JSON")
    lines.append("Ledger:   EXPERIMENTS.md updated.")
    return "\n".join(lines)


def main(argv) -> int:
    if len(argv) != 2:
        print("usage: pr_summary.py <results.json>", file=sys.stderr)
        return 2
    with open(argv[1]) as f:
        rec = json.load(f)
    print(summarize(rec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
