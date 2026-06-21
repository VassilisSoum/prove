import score


def test_correct_scores_pass():
    assert score.classify("900", "900") == "pass"


def test_known_wrong_scores_wrong():
    assert score.classify("300", "900", wrong="300") == "wrong"


def test_other_wrong_scores_fail():
    assert score.classify("123", "900", wrong="300") == "fail"


def test_declined_scores_inconclusive():
    assert score.classify("", "900") == "inconclusive"
    assert score.classify("none", "900") == "inconclusive"


def test_empty_like_expected_still_passes():
    # regression: classify must check `expected` BEFORE the empty-token set, so an
    # empty-ish expected value ("none", "n/a") is matched, not mis-scored inconclusive.
    assert score.classify("none", "none") == "pass"
    assert score.classify("n/a", "n/a") == "pass"


def test_wrong_takes_precedence_over_empty_set():
    # output that equals the known-wrong token is `wrong`, even if it looks empty-ish
    assert score.classify("unknown", "900", wrong="unknown") == "wrong"
