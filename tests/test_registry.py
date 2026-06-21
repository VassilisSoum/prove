import importlib

import pytest


def fresh_registry():
    import registry
    importlib.reload(registry)
    return registry


def test_duplicate_arm_name_raises():
    reg = fresh_registry()
    with pytest.raises(ValueError):
        reg.register(reg.Arm(name="floor", run=lambda c: "x"))   # 'floor' already registered by demo


def test_validate_passes_on_demo():
    reg = fresh_registry()
    reg.validate()   # demo has exactly one floor + outcome cases with expected


def test_validate_requires_one_floor():
    reg = fresh_registry()
    reg.ARMS.clear()
    reg.register(reg.Arm(name="a", run=lambda c: "x"))   # no floor
    reg.register(reg.Arm(name="b", run=lambda c: "y"))
    with pytest.raises(ValueError):
        reg.validate()


def test_validate_requires_expected_on_outcome_case():
    reg = fresh_registry()
    reg.CASES.append(reg.Case(id="bad", expected=""))   # outcome case with no expected
    with pytest.raises(ValueError):
        reg.validate()


def test_pr_summary_formats_block():
    import pr_summary
    rec = {"hypothesis": "X beats Y", "verdict": "REVIEW",
           "decision": "REVIEW — coverage up, but introduces corrupting failures the floor avoided",
           "best": "cand", "best_lift": 0.17, "trials": 1, "cases": 6,
           "arms": {"cand": {"pass": 5, "n": 6, "pass_rate": 0.83}},
           "numeric_findings": [], "cautions": ["a", "b"]}
    out = pr_summary.summarize(rec)
    assert "PROVE REPORT" in out
    assert "Verdict:  REVIEW" in out
    assert "Cautions: 2" in out
