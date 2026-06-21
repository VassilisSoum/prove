# prove

A Claude Code plugin that packages one habit: **measure a change before you ship it.**

It's a project-agnostic, measure-before-you-ship discipline: every behavior change
goes through a falsifiable loop, and *negative results are first-class*. Drop it into
any project and the same rigor is available without re-deriving it.

## What's in the box

| Component | Kind | What it does |
|---|---|---|
| `empirical-method` | skill | The playbook: the 8-step loop, the falsifiability table, the anti-patterns. Auto-triggers when you're about to claim an improvement or ship/approve a behavior change. |
| `scaffold-benchmark` | skill | Measures a proposed change *for* you: reads the diff/functions, scaffolds `bench/`, writes the arms + a starter case set (incl. adversarial), runs it, reports the verdict. You ask the question and eyeball the cases. |
| `experimentalist` | agent | An independent reviewer that gates approval on measured evidence — refuses vague claims, recommends revert on no measured benefit. |
| `templates/bench/` | scaffold | A tiny, dependency-free, runnable harness: arm registry + floor baseline, deterministic outcome scorer, trials runner, and an append-only `EXPERIMENTS.md` ledger. |

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
