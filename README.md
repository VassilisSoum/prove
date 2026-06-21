# prove

A Claude Code plugin that packages one habit: **measure a change before you ship it.**

It's a project-agnostic, measure-before-you-ship discipline: every behavior change
goes through a falsifiable loop, and *negative results are first-class*. Drop it into
any project and the same rigor is available without re-deriving it.

## What's in the box

| Component | Kind | What it does |
|---|---|---|
| `empirical-method` | skill | The playbook: the 8-step loop, the falsifiability table, the anti-patterns. Auto-triggers when you're about to claim an improvement or ship/approve a behavior change. |
| `scaffold-benchmark` | skill | Drops the `bench/` harness into the current project and adapts it to the language. |
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

Then in any project:

```
/prove:scaffold-benchmark      # drop bench/ in
/prove:empirical-method        # load the playbook when designing an experiment
```

and delegate experiment design/result review to the `experimentalist` agent.

## Quickstart (the harness, standalone)

```bash
python templates/bench/run.py \
  --hypothesis "reading the latest value beats taking the first" \
  --lever "value-selection: first vs latest" --trials 5
```

You'll get a per-arm lift table, a KEEP/REVERT verdict, a JSON in
`templates/bench/results/`, and a new row in `templates/bench/EXPERIMENTS.md`.

## Example: using it in a project

Say your project has a search ranker and someone wants to swap exact keyword
matching for a "fuzzy" substring ranker, on the hunch that it's better. Instead of
believing the hunch, measure it.

**1. Scaffold the harness into the repo**

```
/prove:scaffold-benchmark
```

drops `bench/` at the repo root (`registry.py`, `score.py`, `run.py`, `EXPERIMENTS.md`).

**2. Point the arms at your real code** — edit `bench/registry.py`. One lever (the
ranking method), a floor (the current production ranker), equal budget (both arms see
the same queries), scored on the real outcome (did the top hit equal the right doc?):

```python
import search  # your project's module under test

CASES = [
    Case(id="q1", payload={"query": "how do I reset my password"}, expected="auth/reset.md"),
    Case(id="q2", payload={"query": "rotate the api keys"},        expected="security/keys.md"),
    Case(id="q3", payload={"query": "perform db migrations"},      expected="db/migrate.md"),
    # ... ideally drawn from real usage, including queries the candidate might get WRONG
]

register(Arm(name="keyword", is_floor=True,                              # current production
             run=lambda c: search.keyword_search(c.payload["query"])[0]))
register(Arm(name="fuzzy",                                               # the proposed change
             run=lambda c: search.fuzzy_search(c.payload["query"])[0]))
```

**3. Run it**

```bash
python bench/run.py --hypothesis "fuzzy ranking beats keyword ranking" \
                    --lever "ranking: exact-overlap vs +substring" --trials 5
```

```
  keyword          pass  30/40 ( 75%)  (floor)
  fuzzy            pass  40/40 (100%)   lift +25%

verdict: KEEP — measured benefit  (best candidate: fuzzy, lift +25%)

cautions (the verdict above is only as trustworthy as these allow):
  ⚠ Metric is DETERMINISTIC — trials added no information: effective n = 8 cases, not 40.
  ⚠ Small case set (n=8). A lift here is SUGGESTIVE, not decisive. Add cases — especially
    ADVERSARIAL ones that probe where the candidate should FAIL, not only where it should win.
recorded -> results/<ts>.json  and a row in EXPERIMENTS.md
```

**4. Gate it with an independent review** (separate authoring from judging):

> Have the `experimentalist` review this experiment.

The reviewer checks the design and the result and may **overrule a green verdict** — here it
returns `REVERT`, because the case set is small, hand-authored by the change's author, and has
no cases probing fuzzy matching's false positives. That gap between "the harness says KEEP" and
"the review says not yet" is the whole point: the number is necessary, not sufficient.

**5. The ledger remembers.** Every run appends a row to `bench/EXPERIMENTS.md` — wins *and*
the reverted attempts — so the same idea isn't re-tried on a hunch six months later.

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
