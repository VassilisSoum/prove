# Experiments ledger

The durable, append-only record of every measured change — **wins and negatives alike**.

A change ships **only** when a row here shows a measured benefit over the floor, beyond noise.
"No benefit" is a result, not a non-event: record it and revert. This is what stops the same
attractive-but-unproven idea from being re-tried on faith three months later.

`run.py` appends one row per experiment automatically. Add a **Notes** subsection by hand for
anything the table can't hold (variance seen, why you trust/distrust it, follow-ups).

> The most valuable rows are the negatives — e.g. "tuning threshold X measured no benefit,
> reverted"; "approach B beat the default on currency, kept". They stop a disproven idea from
> being re-tried on faith later.

| date (UTC) | hypothesis | lever (the ONE thing changed) | trials | best candidate (pass-rate, lift vs floor) | decision |
|---|---|---|---|---|---|
| 20260621T222915Z | set-based membership beats naive rescans (fewer comparisons) | membership impl: naive scan vs set | 5 | setbased (+95% vs floor on 3 numeric case(s)) | KEEP — measured benefit ⚠×2 |

## Notes

### 20260621T222915Z — count_setbased vs count_naive (numeric)
Sample row from running this example (`python bench/run.py --trials 5`). The metric is the
exact number of element comparisons (`direction="lower"`). set-based membership uses ~95% fewer
comparisons across all three workloads; the bootstrap CI of the difference excludes 0, so the
win is real, not noise. The metric is deterministic, so the harness notes trials add no
information — n=3 cases is suggestive; grow the workload set before trusting broadly.
