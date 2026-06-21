---
name: scaffold-benchmark
version: 0.1.0
description: >
  Drop the `prove` toolkit's `bench/` harness into the current project so a change can be
  measured before it ships. Use when a project has no benchmark/eval harness and
  you're about to test an improvement, tune a parameter, swap a model/algorithm,
  or compare approaches — and the empirical-method loop needs somewhere to run.
  Detects the project's language and instantiates the runner accordingly, keeping
  the structure and the EXPERIMENTS.md ledger constant.
license: MIT
---

# Scaffold the `bench/` harness

This skill installs the runnable half of the `prove` toolkit into a project. The
methodology lives in the `empirical-method` skill; this gives it a place to run.

## Steps

1. **Check for an existing harness.** Look for `bench/`, `eval/`, `benchmarks/`, or
   a test-based eval already in the repo. If one exists, prefer extending it over
   adding a parallel one — tell the user what you found and ask before duplicating.

2. **Detect the project language.** Inspect manifests: `pyproject.toml` / `setup.py`
   → Python; `package.json` → Node/TS; `go.mod` → Go; `Cargo.toml` → Rust; etc.

3. **Copy the template in.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/bench/` to
   `bench/` at the repo root:
   - `EXPERIMENTS.md`, `README.md`, and `results/.gitkeep` are **language-agnostic —
     copy verbatim.**
   - `registry.py`, `score.py`, `run.py` are the **reference (Python) implementation.**

4. **Instantiate the runner for the language.**
   - **Python project:** keep the reference files as-is.
   - **Other language:** port `registry` / `score` / `run` to that language,
     preserving the contract exactly (see below). Keep `EXPERIMENTS.md` and the
     `results/<timestamp>.json` output format identical so the ledger is uniform
     across projects. Wire it to the project's test runner if natural
     (e.g. an npm script, a `go test` target).

5. **Leave the DEMO in place, clearly marked.** The template ships a labelled demo
   experiment so the harness runs immediately. Do **not** silently delete it —
   point the user at the `DELETE THIS BLOCK` marker in `registry.py` and offer to
   replace it with their first real experiment.

6. **Smoke-test it.** Run the harness once (`python bench/run.py`, or the ported
   equivalent). Confirm a per-arm table prints, a JSON lands in `bench/results/`,
   and a row is appended to `bench/EXPERIMENTS.md`. Report the output.

## The contract every port must preserve

- **Arm registry** with exactly one **floor** baseline; all arms run over the same
  cases at **equal budget**.
- **Deterministic classifier** returning `pass` / `fail` / `inconclusive` by
  matching the arm's **real output** against the case's `expected` token (never a
  proxy). `inconclusive` is distinct from `fail`.
- **Runner** that does: trials per (arm, case) → aggregate pass-rate → **lift vs
  floor** → KEEP/REVERT verdict → write `results/<ts>.json` + append an
  `EXPERIMENTS.md` row, **always** (negatives recorded too).

## After scaffolding

Use the `empirical-method` skill to design the first real experiment, and hand the
design and the result to the `experimentalist` agent for an independent gate.
