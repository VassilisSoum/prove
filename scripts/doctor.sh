#!/usr/bin/env bash
# doctor.sh — verify the prove plugin is well-formed and runnable.
# Checks: required files exist, manifests parse, plugin.json and marketplace agree,
# Python compiles, the example harness matches the template, and the example runs.
# Exits non-zero on the first failure. Safe to run in CI.

set -u
cd "$(dirname "$0")/.." || exit 2
ROOT="$(pwd)"
PY="${PYTHON:-python3}"
fail=0

ok()   { printf '  \033[32mok\033[0m   %s\n' "$1"; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=1; }
have() { [ -e "$1" ] && ok "$1" || bad "missing: $1"; }

echo "prove doctor — repo: $ROOT"

echo "== required files =="
have ".claude-plugin/plugin.json"
have ".claude-plugin/marketplace.json"
have "skills/empirical-method/SKILL.md"
have "skills/scaffold-benchmark/SKILL.md"
have "agents/experimentalist.md"
have "templates/bench/registry.py"
have "templates/bench/score.py"
have "templates/bench/run.py"
have "templates/bench/EXPERIMENTS.md"
have "README.md"
have "LICENSE"

echo "== manifests parse + versions agree =="
"$PY" - <<'PYEOF' || fail=1
import json, sys
p = json.load(open(".claude-plugin/plugin.json"))
m = json.load(open(".claude-plugin/marketplace.json"))
entry = m["plugins"][0]
vs = {p["version"], m["version"], entry["version"]}
if len(vs) != 1:
    print(f"  FAIL version mismatch: plugin={p['version']} marketplace={m['version']} entry={entry['version']}")
    sys.exit(1)
if p["name"] != entry["name"]:
    print(f"  FAIL name mismatch: plugin={p['name']} entry={entry['name']}")
    sys.exit(1)
print(f"  ok   manifests parse; name={p['name']} version={p['version']}")
PYEOF

echo "== python compiles =="
if "$PY" -m compileall -q templates/bench examples >/dev/null 2>&1; then
    ok "templates/ + examples/ compile"
else
    bad "python compile error"
fi

echo "== example harness matches the template (no drift) =="
for ex in examples/*/; do
    [ -d "$ex/bench" ] || continue
    for f in run.py score.py; do
        if diff -q "templates/bench/$f" "$ex/bench/$f" >/dev/null 2>&1; then
            ok "${ex}bench/$f == templates/bench/$f"
        else
            bad "drift: ${ex}bench/$f differs from templates/bench/$f"
        fi
    done
done

echo "== examples run =="
# Run in a throwaway copy so the check never mutates the tracked example
# (run.py appends to EXPERIMENTS.md and writes results/).
for ex in examples/*/; do
    [ -d "$ex/bench" ] || continue
    tmp="$(mktemp -d)"
    cp -r "$ex" "$tmp/ex"
    if ( cd "$tmp/ex" && "$PY" bench/run.py --trials 2 >/dev/null 2>&1 ); then
        ok "$ex ran (exit 0)"
    else
        bad "$ex failed to run"
    fi
    rm -rf "$tmp"
done

echo "== unit tests (if pytest available) =="
if "$PY" -c "import pytest" >/dev/null 2>&1; then
    if "$PY" -m pytest -q >/dev/null 2>&1; then ok "pytest passed"; else bad "pytest failed"; fi
else
    ok "pytest not installed — skipping (CI runs it)"
fi
rm -rf templates/bench/__pycache__ tests/__pycache__ 2>/dev/null

echo
if [ "$fail" -eq 0 ]; then
    printf '\033[32mAll checks passed.\033[0m\n'
else
    printf '\033[31mSome checks failed.\033[0m\n'
fi
exit "$fail"
