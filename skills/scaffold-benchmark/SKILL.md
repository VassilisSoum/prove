---
name: scaffold-benchmark
version: 0.2.0
description: >
  Measure a proposed change for the developer — author and run the experiment, don't
  hand them a blank template. Use when someone asks "is X better?", "should I ship
  this?", "did this improve Y?", or proposes swapping/tuning an implementation. Reads
  the change from the code (git diff / the named functions), scaffolds the bench/
  harness if absent, WRITES the arms + a starter case set (including adversarial
  cases) by reading the repo, shows the cases for a quick human OK, runs it, and
  reports the verdict. The developer's whole job is: ask the question, eyeball the
  cases, read the result.
license: MIT
---

# Measure a change (author + run the experiment)

A developer will not sit and hand-write a benchmark. So don't ask them to. When a
change claims to improve a measurable behavior, **you** author the experiment from
the code and run it; the developer only states the question, sanity-checks the
drafted cases, and reads the verdict.

This skill carries the runnable half of the `prove` toolkit (the `bench/` harness).
The discipline it follows is the `empirical-method` skill; the independent gate is
the `experimentalist` agent.

## The flow

1. **Identify the change and the one lever.** Find what's being compared, from
   (in order): the `git diff` / PR, an explicitly named old-vs-new function or
   module, or — only if none of those are clear — a single question to the developer
   ("what's the candidate, and what does it replace?"). The thing it replaces is the
   **floor**; the proposal is the **candidate**. Exactly one lever differs.

2. **Ensure `bench/` exists** (scaffold sub-step, only if not already present):
   - Check for an existing harness (`bench/`, `eval/`, `benchmarks/`, a test-based
     eval). If one exists, extend it rather than duplicate — say what you found first.
   - Detect the language (`pyproject.toml`/`setup.py`→Python, `package.json`→Node,
     `go.mod`→Go, `Cargo.toml`→Rust, …).
   - Copy `${CLAUDE_PLUGIN_ROOT}/templates/bench/` to `bench/` at the repo root.
     `EXPERIMENTS.md`, `README.md`, `results/.gitkeep` copy verbatim; for non-Python,
     port `registry`/`score`/`run` preserving the contract (below).

3. **Author `registry.py` from the code.** This is the point of the skill — write it,
   don't leave a blank:
   - Wire arm **floor** to the current implementation and arm **candidate** to the
     proposal, calling the **real functions** (add the project root to `sys.path` /
     import path so the harness can import the module under test).
   - **Draft a starter case set by mining the repo:** existing unit tests, docstring
     examples, fixtures, README samples, sample data. Reuse their known-correct
     answers as gold labels wherever they exist — those are trustworthy because the
     developer already wrote them.
   - **Always include at least one ADVERSARIAL case** that probes where the candidate
     could fail (an ambiguous input, an edge value, a known footgun of the new
     approach) — not only inputs it should win on. If you can't think of one, say so;
     a happy-path-only set is the most common way a benchmark lies.
   - Keep **equal budget** (same inputs to both arms) and **real-outcome scoring**
     (compare the value produced, not a proxy). Map a "no answer / declined" return to
     an empty string so it scores `inconclusive` (a silent miss), distinct from a
     confidently wrong `fail`.

4. **Show the developer the drafted experiment for a 10-second OK.** Print a compact
   list: the two arms, and each case as `input → expected (why)`. Ask them to confirm
   or correct. **This is the one irreducible human step** — if the gold labels are
   wrong the verdict is worthless, and you must not invent answers you can't justify.
   For any case whose correct answer you're unsure of, mark it `?` and ask rather than
   guess. (The `experimentalist` will also challenge self-authored / unverified labels.)

5. **Run it and report.** `python bench/run.py --hypothesis "…" --lever "…" --trials N`
   (or the ported equivalent). Show the per-arm lift table, the KEEP/REVERT verdict,
   and any cautions. Read the columns, not just the headline: a coverage win that adds
   a *corrupting* failure is not a win.

6. **Offer the independent gate.** Hand the result to the `experimentalist` agent for
   a verdict before anything ships. The run already appended a row (negatives included)
   to `bench/EXPERIMENTS.md`.

## The contract every port must preserve

- **Arm registry** with exactly one **floor** baseline; all arms run over the same
  cases at **equal budget**.
- **Deterministic classifier** returning `pass` / `fail` / `inconclusive` by matching
  the arm's **real output** against the case's `expected` token (never a proxy).
  `inconclusive` is distinct from `fail`.
- **Runner**: trials per (arm, case) → aggregate pass-rate → **lift vs floor** →
  KEEP/REVERT verdict → write `results/<ts>.json` + append an `EXPERIMENTS.md` row,
  **always** (negatives recorded too).

## What stays the developer's call

You draft; they decide. The labels (what "correct" means) and the final ship/revert
decision are theirs — but the friction of *building* the experiment is now yours, not
theirs. That asymmetry is the whole point: "confirm these 6 cases" is a thing a busy
developer will actually do; "write this benchmark file" is not.
