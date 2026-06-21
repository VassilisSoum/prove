# prove

[![ci](https://github.com/VassilisSoum/prove/actions/workflows/ci.yml/badge.svg)](https://github.com/VassilisSoum/prove/actions/workflows/ci.yml)

**Stop shipping changes on vibes.**

`prove` is the scientific method for Claude Code. When a change claims to be *better* —
a new ranker, a faster path, a tuned threshold, a different prompt or model — `prove`
compares a **baseline** against the **candidate** under **equal budget**, scores the
**real outcome** (not proxy confidence), and returns a **KEEP / REVIEW / REVERT**
verdict. Every experiment — wins and negatives alike — is recorded in `EXPERIMENTS.md`.

It's three things working together: a methodology skill, an independent reviewer agent,
and a small dependency-free benchmark harness. You bring the question; the plugin builds
and runs the experiment and an agent gates the result before you ship. It's a guided
workflow inside Claude Code — not a standalone autonomous CLI, and not a substitute for
your tests.

## What's in the box

| Component | Kind | What it does |
|---|---|---|
| `empirical-method` | skill | The playbook: the 8-step loop, the falsifiability table, the anti-patterns. Auto-triggers when you're about to claim an improvement or ship/approve a behavior change. |
| `scaffold-benchmark` | skill | Measures a proposed change *for* you: reads the diff/functions, scaffolds `bench/`, writes the arms + a starter case set (incl. adversarial), runs it, reports the verdict. You ask the question and eyeball the cases. |
| `experimentalist` | agent | An independent reviewer that gates approval on measured evidence — refuses vague claims, recommends revert on no measured benefit. |
| `templates/bench/` | scaffold | A tiny, dependency-free, runnable harness: arm registry + floor baseline, outcome **and** numeric scoring (with a bootstrap noise-band), a trials runner, and an append-only `EXPERIMENTS.md` ledger. |

## When should I use Prove?

Prove is **not for every PR**. Use it when a change claims to be **better, not merely
different** — where "better" is a measurable outcome.

**Good fits**
- AI / RAG / prompt / reranking changes
- Performance improvements
- Fraud / risk / scoring logic
- Reconciliation logic
- Retry / failure-handling changes
- Any PR claiming "X is better than Y"

**Poor fits** (skip Prove)
- Pure refactors
- Formatting
- Simple CRUD changes
- Dependency bumps — unless they claim measurable impact
- Bug fixes already covered by deterministic tests

> **Use Prove whenever a change claims to be _better_, not merely _different_.**

## The loop

1. State a falsifiable **hypothesis**.
2. Isolate **one lever**.
3. Define the arms, including a real **floor baseline**.
4. Compare at **equal budget**.
5. Score on the **real outcome**, not a proxy.
6. Run **enough trials** for the variance.
7. **Keep only on measured benefit — else revert.**
8. **Record it durably**, wins and negatives alike.

## Install

```bash
# from anywhere
/plugin marketplace add VassilisSoum/prove
/plugin install prove@prove
```

> Developing locally? Point the marketplace at the repo on disk instead:
> `/plugin marketplace add /path/to/prove`

Then in any project, just ask — you don't hand-write a benchmark:

```
Should I ship parse_date_v2 instead of parse_date?
```

`prove` reads the change, scaffolds `bench/`, writes the arms + cases, runs it, and
reports the verdict. You confirm the drafted cases and read the result; the
`experimentalist` agent gives the independent gate before anything ships.

(Explicit entry points if you want them: `/prove:scaffold-benchmark` to measure a
change, `/prove:empirical-method` to load the methodology.)

## Verify your install

From a clone of this repo:

```bash
bash scripts/doctor.sh
```

It checks that the plugin/skill/agent/template files exist, the manifests parse and
agree on version, the Python compiles, the bundled examples match the template (no
drift), the examples run, and the unit tests pass (`pytest`, if installed). CI runs the
same script — plus the test suite — on every push and PR.

## Quickstart (the harness, standalone)

```bash
python templates/bench/run.py \
  --hypothesis "reading the latest value beats taking the first" \
  --lever "value-selection: first vs latest" --trials 5
```

You'll get a per-arm lift table, a KEEP/REVERT verdict, a JSON in
`templates/bench/results/`, and a new row in `templates/bench/EXPERIMENTS.md`.

(In this repo the harness lives under `templates/bench/`. Once `scaffold-benchmark`
drops it into a project it's just `bench/` — which is why the example below uses the
shorter `bench/` paths.)

## Example: using it in a project

Your project has a search ranker, and someone wants to swap exact keyword matching
for a "fuzzy" substring ranker, on the hunch it's better. You don't believe the
hunch — and you don't hand-write a benchmark either. You ask:

> Should we switch search ranking from keyword to fuzzy? Measure it.

`prove` does the rest:

**1. It authors the experiment** — reads your `search.py`, scaffolds `bench/`, and
writes `bench/registry.py`: floor = the current `keyword_search`, candidate =
`fuzzy_search`, both over the same queries (equal budget), scored on the real outcome
(did the top hit equal the right doc?). It drafts cases from your tests/usage and adds
an adversarial one, then shows them for a 10-second OK:

```
arms:  keyword (floor)  vs  fuzzy
cases: "how do I reset my password"  -> auth/reset.md
       "rotate the api keys"         -> security/keys.md
       "perform db migrations"       -> db/migrate.md
       "keynote scheduling" (adv.)   -> (no match)  — 'key' must NOT rank security/keys.md
confirm or correct these labels?
```

**2. It runs it**

```
  keyword          pass  30/40 ( 75%)  (floor)
  fuzzy            pass  40/40 (100%)   lift +25%

verdict: KEEP — measured benefit  (best candidate: fuzzy, lift +25%)
cautions:  ⚠ deterministic metric (effective n = 8, not 40)   ⚠ small case set (n=8)
recorded -> results/<ts>.json  and a row in EXPERIMENTS.md
```

**3. It gates the result with an independent review** — the `experimentalist` checks
the design and the result and may **overrule a green verdict**; here it returns
`REVERT`, because the case set is small, self-authored, and thin on adversarial cases.
That gap between "the harness says KEEP" and "the review says not yet" is the point:
the number is necessary, not sufficient.

**4. It records it** — every run appends a row to `bench/EXPERIMENTS.md` (wins *and*
reverts), so the idea isn't re-tried on a hunch six months later.

Your total effort: one question, a glance at the drafted cases, a read of the verdict.

> Two fully **runnable** examples live in [`examples/`](examples/):
> [`simple-ranking/`](examples/simple-ranking/) (outcome scoring — `pass` / `wrong` /
> `inconclusive` and a REVIEW verdict where the candidate gains coverage but introduces
> one confidently-wrong answer the floor avoided) and
> [`numeric-cost/`](examples/numeric-cost/) (a **numeric** metric — median/p95 + a
> bootstrap confidence interval). Clone the repo and `python bench/run.py`.

## Outcome vs numeric metrics

A case is one of two kinds:

- **outcome** (default) — the arm returns a token scored `pass` / `wrong` / `fail` /
  `inconclusive`. A confidently-wrong answer (`wrong`/`fail`) is treated as worse than a
  safe abstention (`inconclusive`).
- **numeric** — set `kind="numeric"` and `direction="lower"|"higher"`; the arm returns a
  number (latency, cost, throughput…). The runner reports median/mean/p95 and a **bootstrap
  confidence interval of (candidate − floor)**, so a stochastic "+X%" only counts as a win
  if it's beyond run-to-run noise; a metric that regresses beyond noise is flagged.

`--verbose` prints a per-case × arm table; every result JSON also records per-case detail.

## Using Prove with Pull Requests

Prove isn't a required gate on every PR — run it on the ones that make a measurable
claim. Two ways:

- **Manually, before merge** — when a PR says "X is better than Y", ask Prove the
  question, confirm the drafted cases, read the verdict, and paste a short summary into
  the PR.
- **In CI (optional)** — wire `bench/run.py` into a job for changes that touch a measured
  component and post the result as a PR comment.

Example questions a PR might ask:
- "Should we ship `retrieval_v2` instead of `retrieval_v1`?"
- "Should we ship the async reconciliation worker instead of the current worker?"
- "Should we ship the new retry policy instead of the existing one?"

An example summary you'd write in the PR (Prove gives you the numbers and the verdict;
you phrase the takeaway):

```
PROVE REPORT
Question: Should we ship async_reconciliation instead of current_reconciliation?
Verdict:  REVIEW
Reason:   Candidate improves throughput by 31%, but introduces 3 duplicate-processing
          outcomes the current worker avoided (confidently-wrong > safe abstention).
Ledger:   EXPERIMENTS.md updated.
```

For a typical backend project, only a small fraction of PRs need Prove — the ones whose
value rests on a measurable claim.

**Gating a CI job.** `bench/run.py` takes `--fail-on` so a job can block on the verdict,
and `scripts/pr_summary.py` turns the result JSON into the PROVE REPORT block above:

```bash
python bench/run.py --trials 25 --fail-on REVERT,REVIEW \
  --hypothesis "ship retrieval_v2 instead of retrieval_v1?" --lever "retriever: v1 -> v2"
python scripts/pr_summary.py bench/results/*.json   # post this as a PR comment
```

(`--fail-on` is opt-in — by default Prove is advisory and never blocks.)

## Design notes

- **Advisory, not enforced.** No hooks, nothing blocks your tools. The discipline is
  carried by the skill and enforced socially by the reviewer agent — which also keeps
  authoring and judging in separate passes.
- **Why a plugin and not just a skill.** Skills are pure markdown and can't bundle
  runnable scripts. The methodology has a mechanizable half (the harness) that needs
  real files, so the toolkit is a plugin: skill + agent + scaffold together.

## Why these rules

Each rule kills a specific way a benchmark lies to you: the floor stops absolute
numbers from masquerading as improvements; equal budget stops an unfair advantage
reading as a better approach; real-outcome scoring stops a proxy that correlates with
success from standing in for it; trials stop a lucky run; the ledger stops disproven
ideas from being re-tried on faith.

## Known limitations

Prove produces **evidence and a decision record**, not a proof. Read results with these
in mind:

- **Tiny benchmark sets are weak evidence.** A lift across a handful of cases is
  suggestive, not decisive — grow the set, especially with adversarial cases.
- **Deterministic repeated trials are not independent evidence.** Re-running a
  deterministic metric N times is n=1 repeated N times; the effective sample size is the
  number of *cases*. The harness flags this.
- **Claude-authored cases need a human eye.** The plugin drafts cases and labels; if the
  gold labels are wrong, the verdict is worthless. Confirm them.
- **Prove does not replace unit or integration tests.** It compares approaches on an
  outcome; it doesn't verify a change is correct in isolation. Keep your test suite.
- **It's strongest when the outcome is objectively measurable.** For decisions that hinge
  on incommensurable trade-offs (architecture, ops burden, cost), Prove measures only the
  measurable slice — the rest is design judgment.
- **The experimentalist reviewer is a guardrail, not a mathematical proof.** It catches
  common ways a benchmark misleads; it can still miss things.
