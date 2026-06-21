---
name: empirical-method
version: 0.1.0
description: >
  Measure a change before you ship it. Use this skill BEFORE claiming an
  improvement, optimization, or fix works — and before approving, merging, or
  shipping a behavior change. It installs a falsifiable loop: hypothesis →
  isolate one lever → fair floor baseline at equal budget → score on the real
  outcome (not a proxy) → enough trials for the variance → keep only on measured
  benefit, else revert → record the result (incl. negatives) durably. Trigger
  whenever you catch yourself saying "this is faster / better / fixes it" without
  a number, when tuning a parameter or swapping a model/algorithm/prompt, or when
  asked to evaluate or benchmark anything.
license: MIT
---

# The empirical method

The point is not ceremony —
it is to stop shipping changes that *feel* better but aren't, and to stop
re-trying ideas that were already disproven. Every behavior change earns its place
with a measured benefit, or it gets reverted.

## When this applies

Invoke the loop whenever a change is meant to **improve a measurable behavior**:
a faster path, a better prompt, a smarter retrieval, a tuned threshold, a new
model. It does **not** apply to changes with no behavioral claim (a rename, a
docstring, a pure refactor that's verified by the test suite).

Red flags that you're about to skip it: *"this should be faster," "this is
clearly better," "let's just ship it," "the new model is smarter."* Each is a
hypothesis with no measurement attached.

## The loop

1. **State the hypothesis.** One sentence, falsifiable. "Switching the extractor
   to model X raises capture accuracy." Not "X is better."

2. **Isolate one lever.** Identify the single variable you're changing. If you're
   changing two things (new model *and* new prompt), you can't attribute the
   result — split into two experiments.

3. **Define the arms, including a real floor.** An *arm* is one approach. Always
   include a **floor baseline** — the do-nothing / trivial approach — so lift is
   measured against something real, not a strawman. Add naive/ceiling arms when
   they sharpen interpretation.

4. **Equal budget.** Give every arm the same inputs, same context size, same
   retries, same resource limits. The only thing that differs is the lever. An
   unfair budget is the most common way a benchmark lies.

5. **Score on the real outcome, not a proxy.** Measure what you actually care
   about — the task completing, the correct value being written — not a number
   that merely correlates with it. High recall@k that still gets the task wrong
   is a worse-than-useless metric.

6. **Run enough trials for the variance.** A single trial on a stochastic metric
   (anything touching an LLM, sampling, timing) is noise. Run N trials per
   (arm, case); if the metric is high-variance, raise N until the signal is stable.
   Report the spread, not just the mean. Be explicit when a result is small-n,
   synthetic, or merely directional.

7. **Decide: keep only on measured benefit, else revert.** If the candidate beats
   the floor beyond noise → keep. If it ties or regresses → **revert**, even if the
   idea was theoretically attractive. "No measured benefit" is a complete,
   respectable result.

8. **Record it durably — wins and negatives alike.** Append the result to the
   experiments ledger (`bench/EXPERIMENTS.md`): hypothesis, lever, arms, metric,
   trials, outcome, decision. The negative results are the most valuable entries —
   they stop the same idea being re-litigated on faith later.

## Falsifiability — name the kill condition up front

Before running, write the condition under which the hypothesis is **false**. If you
can't state one, you don't have an experiment.

| claim shape | falsification condition |
|---|---|
| "Candidate improves metric M" | candidate's M ≤ floor's M, within run-to-run noise |
| "Change has no regression" | any tracked outcome worsens beyond noise |
| "A is better than B" | A's outcome ≤ B's at equal budget |
| "This fixes the bug" | the failing case still fails after the change |

## Anti-patterns (each one fools you into shipping noise)

- **Proxy worship.** Optimizing a correlate (latency, recall@k, token count)
  instead of the outcome you actually want.
- **Two levers at once.** Can't attribute the result to either; you've learned
  nothing.
- **Strawman baseline.** Beating a crippled competitor proves nothing. The floor
  must be the honest do-nothing/naive approach — including a sensible tie-break. A
  floor with a pathological fallback (e.g. "on no match, return the first item")
  inflates every candidate's lift.
- **n=1 on a noisy metric.** One lucky run is not a result.
- **Trials that aren't trials.** Running a *deterministic* metric N times is n=1
  repeated N times — the effective sample size is the number of cases, not trials.
  It looks like more evidence than it is.
- **Happy-path-only cases.** Testing the candidate only where it should win. Always
  include adversarial cases that probe where it should **fail** (a fuzzy matcher's
  false positives, an optimization's worst input) — that's where regressions hide.
- **Self-authored gold set.** The same person writing the change *and* hand-picking
  the cases and their "correct" answers drifts the test toward the change's
  strengths. Draw cases from real usage, or have someone else curate them blind to
  the implementation.
- **Silent negatives.** Discarding a "didn't work" without recording it — so it
  gets re-tried in three months.
- **Post-hoc metric.** Choosing the metric *after* seeing which one makes the
  change look good.

## How to run it

- **Don't hand the developer a blank benchmark — author it for them.** When the
  change is concrete code, invoke the **`scaffold-benchmark`** skill: it reads the
  diff/functions, scaffolds `bench/` if needed, writes the arms + a drafted case set
  (including adversarial cases), shows the cases for a quick OK, runs it, and reports
  the lift. The developer's job shrinks to: ask the question, eyeball the cases, read
  the verdict.
- Keep **authoring and judging separate.** Don't approve your own experiment in the
  same pass. Hand the design (before) and the result (after) to the
  **`experimentalist`** agent for an independent gate — it refuses vague claims and
  recommends revert on no measured benefit.
