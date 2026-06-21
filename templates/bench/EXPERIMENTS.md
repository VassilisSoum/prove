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

## Notes

<!-- e.g.
### 20260621T...Z — latest-value arm vs floor
Lift was +100% across 3 cases at 5 trials each, fully deterministic (no variance).
The demo arms are trivial; the point is the harness wiring, not this result.
-->
