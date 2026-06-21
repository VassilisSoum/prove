# Example: simple-ranking

A small, runnable Prove experiment. It answers one question —

> Should we ship `candidate_rank` instead of `baseline_rank`?

— and shows the distinction at the heart of Prove: **a confidently-wrong answer is
worse than a safe abstention**, and pass-rate alone hides that.

## The setup

`ranking.py` has two ways to rank docs for a query:

- **`baseline_rank`** (the floor / current behaviour): exact keyword overlap. When
  nothing matches it returns `None` — it **abstains**, and the app asks the user.
- **`candidate_rank`** (the proposed change): adds substring matching. It ranks more
  queries, but it **never abstains** — so on inputs it doesn't understand it
  confidently returns a wrong doc.

`bench/registry.py` wires both as arms over the same six queries, scored on the real
outcome (top doc == documented-correct doc). `bench/run.py` and `bench/score.py` are
the Prove harness, copied verbatim from `templates/bench/`.

## Run it

```bash
cd examples/simple-ranking
python bench/run.py --trials 1 \
  --hypothesis "candidate_rank should replace baseline_rank (handles more queries)" \
  --lever "ranking: exact-overlap vs +substring"
```

(Deterministic metric, so one trial is enough — see `expected_output.txt`.)

## What you'll see

```
  baseline    pass 4/6 (67%)  wrong 0  fail 0  inconcl 2  (floor)
  candidate   pass 5/6 (83%)  wrong 1  fail 0  inconcl 0   lift +17%

verdict: REVIEW — coverage up, but introduces corrupting failures the floor avoided
```

Read the columns, not just the headline:

- **`inconclusive` (baseline, 2)** — on the word-variant queries (`"perform db
  migrations"`, `"refunding the customer"`) the floor safely abstains. The candidate's
  substring matching turns those into correct answers — a **genuine win**.
- **`wrong` (candidate, 1)** — on the junk query `"redistribute traffic"` the candidate
  hallucinates: `redis` is a substring of `redi`stribute, so it confidently returns
  `cache/ttl.md`. The floor abstained (correct). This is the cost of "never abstain".
- The verdict is **REVIEW**, not KEEP: the +17% coverage is real, but it's bought with
  a corrupting error the floor never made. The fix is obvious — let the candidate
  abstain when its only signal is a weak substring match — and that becomes the next
  experiment.

`bench/EXPERIMENTS.md` holds the recorded row (this directory ships one as a sample).
