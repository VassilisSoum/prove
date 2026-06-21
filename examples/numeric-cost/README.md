# Example: numeric-cost

A runnable Prove experiment using a **numeric** metric (not a pass/fail outcome). It
answers:

> Should we ship `count_setbased` instead of `count_naive`?

`cost.py` has two membership-check implementations compared on an exact, deterministic
metric — the **number of element comparisons** to answer a batch of "is x in items?"
queries (`direction="lower"` — fewer is better):

- **`count_naive`** (floor): rescans the list for every query — O(targets × items).
- **`count_setbased`** (candidate): builds a set once, then O(1) lookups.

`bench/registry.py` declares each case `kind="numeric", direction="lower"`, so the arms
return a **number** and the runner reports median / mean / p95 and a **bootstrap
confidence interval of (candidate − floor)** to decide whether the improvement is beyond
run-to-run noise.

## Run it

```bash
cd examples/numeric-cost
python bench/run.py --trials 5 --verbose \
  --hypothesis "set-based membership beats naive rescans (fewer comparisons)" \
  --lever "membership impl: naive scan vs set"
```

## What you'll see

```
  numeric[present_500]  floor median 1e+04 -> setbased 520  (+95%, better; 95% CI diff [9480, 9480])
  numeric[present_2000] floor median 4e+04 -> setbased 2020 (+95%, better; ...)
  numeric[absent_1000]  floor median 2e+04 -> setbased 1020 (+95%, better; ...)

verdict: KEEP — measured benefit  (best candidate: setbased)
```

Notes:
- The metric is **exact/deterministic**, so the result is reproducible (good for CI) and
  the harness honestly flags that *trials add no information* for a deterministic metric —
  while the bootstrap CI (which excludes 0 in the improving direction) confirms the
  improvement is real, not noise.
- For a **stochastic** numeric metric (e.g. latency), run more trials; if the CI of the
  difference straddles 0 the verdict drops to **REVIEW** with a "within run-to-run noise"
  caution, and a metric that regresses beyond noise is flagged as a corrupting regression.

See [`../simple-ranking/`](../simple-ranking/) for the outcome (pass/wrong/inconclusive)
variant.
