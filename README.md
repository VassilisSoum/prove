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

## Install (local)

```bash
# from anywhere
/plugin marketplace add ~/IdeaProjects/personal/prove
/plugin install prove@prove
```

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
