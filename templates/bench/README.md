# `bench/` — the prove harness

A tiny, dependency-free harness for **measuring a change before you ship it**. Compare
approaches ("arms") over a set of cases, score each on its **real outcome**, and record the
verdict — including negative results — in `EXPERIMENTS.md`.

This is the runnable half of the `prove` toolkit. The thinking half is the
`empirical-method` skill; the review half is the `experimentalist` agent.

## The contract (3 files, 1 of which you edit)

| file | role | you edit? |
|---|---|---|
| `registry.py` | your experiment: the **arms** and the **cases** | **yes** |
| `score.py` | deterministic **outcome scorer** (pass / fail / inconclusive) | rarely |
| `run.py` | the **runner**: trials, aggregation, lift, ledger | no |

`registry.py` ships with a labelled **DEMO** experiment so the harness runs out of the box.
Delete that block and define your own.

## Run it

```bash
python bench/run.py --hypothesis "reading the latest value beats taking the first" \
                    --lever "value-selection: first vs latest" --trials 5
```

You'll see a per-arm table with **lift vs the floor**, a **KEEP / REVERT** verdict, a JSON
written to `bench/results/`, and a new row in `bench/EXPERIMENTS.md`.

Run a subset of arms: `--arms floor,latest`.

## The four rules the harness enforces for you

1. **Floor baseline.** Mark one arm `is_floor=True` (the do-nothing / trivial approach). Lift
   is always reported against it. Without a floor, "80% pass" is meaningless.
2. **Equal budget.** Every arm sees the same `CASES`. Don't give your candidate more context,
   more retries, or easier inputs than the floor — that's how you fool yourself.
3. **One lever.** An experiment changes exactly one variable. Two changes → two experiments.
4. **Real-outcome scoring.** `score.classify` matches the value the arm actually produced
   against the case's `expected` token. Never score a proxy that merely correlates with success.

## Defining your experiment (`registry.py`)

```python
CASES = [
    Case(id="...", payload={...}, expected="<correct>", wrong="<known-wrong/stale>"),
]

register(Arm(name="floor", is_floor=True, run=lambda c: ...))   # the baseline
register(Arm(name="candidate",            run=lambda c: ...))   # the one lever changed
```

An arm's `run(case)` can do anything — call your code, hit a local service, shell out, ask an
agent — as long as it returns the string to be scored. Keep arms at equal budget.

## Reading the result

- **lift > 0, beyond noise → KEEP.** Add a Notes paragraph in `EXPERIMENTS.md` on the variance
  you saw.
- **lift ≈ 0 or negative → REVERT.** The row stays in the ledger. That negative is the asset:
  it stops the idea being re-tried on faith.
- **high `inconclusive` count** means arms are abstaining — usually a case/wiring problem, not
  a real signal. Fix before trusting pass-rates.
- **noisy metric?** Raise `--trials`. A 1-trial win on a stochastic metric is not a win.

## Don't fool yourself

A green KEEP verdict is only as honest as the experiment behind it. The runner prints
**cautions** when it can detect a problem mechanically, but these are on you:

- **Honest floor, not a strawman.** The floor must be the real do-nothing/current approach,
  including a *sensible* tie-break. A floor rigged to fail (e.g. "on no match, always return the
  first item") makes any candidate look good. If your floor has a pathological fallback, fix the
  fallback before trusting the lift.
- **Adversarial cases, not just wins.** Include cases that probe where the *candidate* should
  **fail**, not only where it should win. A fuzzy matcher tested only on its happy path will
  always look great; add the queries that expose its false positives.
- **Independent labels.** If the same person writes the change *and* hand-picks the cases and
  their "correct" answers, the test set drifts toward the change's strengths. Have someone else
  curate cases, or draw them from real usage, blind to the implementation.
- **Deterministic ≠ proven.** If arms are deterministic, `--trials` just repeats identical runs;
  your effective sample size is the number of **cases**, not trials. The runner flags this. More
  cases strengthen a result; more trials of a deterministic metric do not.
- **Small n is suggestive, not decisive.** A lift across 8 cases is a hint. Before shipping a
  real change, grow the case set (the runner cautions under n=10).

When in doubt, hand the design (before) and the result (after) to the **`experimentalist`** agent —
its whole job is to catch these.

## Other languages

The harness is ~120 lines of stdlib Python on purpose, so it's a readable spec. To port to
Node/Go/Rust, keep the contract identical: an **arm registry** with a floor, a **deterministic
classifier** returning pass/fail/inconclusive, a **runner** that does trials → aggregate → lift
→ write `results/<ts>.json` + append an `EXPERIMENTS.md` row. The `scaffold-benchmark` skill can
generate the equivalent in your project's language.
