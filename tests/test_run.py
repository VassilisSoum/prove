import run

OUT = {"kind": "outcome"}


def _cells(d):
    return {k: list(v) for k, v in d.items()}


def test_clean_win_keeps():
    meta = {"c1": OUT, "c2": OUT}
    cells = _cells({("floor", "c1"): ["fail"], ("floor", "c2"): ["fail"],
                    ("cand", "c1"): ["pass"], ("cand", "c2"): ["pass"]})
    rec = run.aggregate(cells, ["floor", "cand"], "floor", meta, 1)
    assert rec["verdict"] == "KEEP"
    assert rec["best"] == "cand"


def test_no_lift_reverts():
    meta = {"c1": OUT}
    cells = _cells({("floor", "c1"): ["pass"], ("cand", "c1"): ["pass"]})
    rec = run.aggregate(cells, ["floor", "cand"], "floor", meta, 1)
    assert rec["verdict"] == "REVERT"


def test_corrupting_candidate_reviews_not_keeps():
    # cand has higher pass-rate (+lift) but introduces a confident-wrong the floor lacked
    meta = {"c1": OUT, "c2": OUT, "c3": OUT}
    cells = _cells({("floor", "c1"): ["pass"], ("floor", "c2"): ["inconclusive"], ("floor", "c3"): ["inconclusive"],
                    ("cand", "c1"): ["pass"], ("cand", "c2"): ["pass"], ("cand", "c3"): ["wrong"]})
    rec = run.aggregate(cells, ["floor", "cand"], "floor", meta, 1)
    assert rec["verdict"] == "REVIEW"
    assert "corrupting" in rec["decision"]


def test_tiebreak_prefers_fewest_confident_wrong():
    # the proxy-lie regression: two candidates tie on pass-rate; the SAFE one must win,
    # never the one that gets there with a confident-wrong.
    meta = {"c1": OUT, "c2": OUT, "c3": OUT}
    cells = _cells({
        ("floor", "c1"): ["pass"], ("floor", "c2"): ["inconclusive"], ("floor", "c3"): ["inconclusive"],
        ("fuzzy", "c1"): ["pass"], ("fuzzy", "c2"): ["pass"], ("fuzzy", "c3"): ["wrong"],
        ("cons", "c1"): ["pass"], ("cons", "c2"): ["pass"], ("cons", "c3"): ["inconclusive"],
    })
    rec = run.aggregate(cells, ["floor", "fuzzy", "cons"], "floor", meta, 1)
    assert rec["best"] == "cons"          # not the corrupting "fuzzy"
    assert rec["verdict"] == "KEEP"


def test_deterministic_caution_only_when_trials_gt_1():
    meta = {"c1": OUT}
    cells = _cells({("floor", "c1"): ["fail", "fail", "fail"], ("cand", "c1"): ["pass", "pass", "pass"]})
    rec = run.aggregate(cells, ["floor", "cand"], "floor", meta, 3)
    assert any("DETERMINISTIC" in c for c in rec["cautions"])
    rec1 = run.aggregate(_cells({("floor", "c1"): ["fail"], ("cand", "c1"): ["pass"]}),
                         ["floor", "cand"], "floor", meta, 1)
    assert not any("DETERMINISTIC" in c for c in rec1["cautions"])


def test_small_n_and_no_floor_cautions():
    meta = {"c1": OUT}
    rec = run.aggregate(_cells({("a", "c1"): ["pass"], ("b", "c1"): ["pass"]}),
                        ["a", "b"], None, meta, 1)
    assert any("No floor" in c for c in rec["cautions"])
    assert any("Small case set" in c for c in rec["cautions"])


def test_numeric_clear_win_keeps():
    meta = {"n1": {"kind": "numeric", "direction": "lower"}}
    cells = {("floor", "n1"): [10000.0] * 5, ("cand", "n1"): [520.0] * 5}
    rec = run.aggregate(cells, ["floor", "cand"], "floor", meta, 5)
    assert rec["verdict"] == "KEEP"
    assert rec["numeric_findings"][0]["verdict"] == "better"


def test_numeric_within_noise_reviews():
    meta = {"n1": {"kind": "numeric", "direction": "lower"}}
    cells = {("floor", "n1"): [10.0] * 5, ("cand", "n1"): [10.0] * 5}   # identical -> no improvement
    rec = run.aggregate(cells, ["floor", "cand"], "floor", meta, 5)
    assert rec["verdict"] == "REVIEW"
    assert rec["numeric_findings"][0]["verdict"] == "within-noise"


def test_numeric_regression_reverts():
    meta = {"n1": {"kind": "numeric", "direction": "lower"}}
    cells = {("floor", "n1"): [10.0] * 5, ("cand", "n1"): [20.0] * 5}   # candidate worse
    rec = run.aggregate(cells, ["floor", "cand"], "floor", meta, 5)
    assert rec["numeric_findings"][0]["verdict"] == "worse"
    assert rec["verdict"] == "REVERT"
