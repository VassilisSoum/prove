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
| 20260621T214334Z | candidate_rank should replace baseline_rank (handles more queries) | ranking: exact-overlap vs +substring | 1 | candidate 83% (lift +17%) | REVIEW — coverage up, but introduces corrupting failures the floor avoided ⚠×2 |

## Notes

### 20260621T214334Z — candidate_rank vs baseline_rank
Sample row from running this example (`python bench/run.py --trials 1`). The +17% lift is real
(two word-variant queries the floor abstained on), but the candidate also produced one confidently
**wrong** result on junk input the floor safely declined — hence REVIEW, not KEEP. A wrong answer
is worse than an abstention. Fix: let the candidate abstain on weak substring-only matches, then
re-run. (Deterministic metric, n=6 — suggestive, not decisive; grow the case set before trusting.)
