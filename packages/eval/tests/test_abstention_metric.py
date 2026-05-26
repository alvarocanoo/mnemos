from mnemos_eval.metrics.abstention import abstention_rate, abstention_score


def test_score_empty_retrieved_is_one():
    assert abstention_score([]) == 1


def test_score_any_retrieved_is_zero():
    assert abstention_score(["a"]) == 0
    assert abstention_score(["a", "b", "c"]) == 0


def test_rate_perfect():
    assert abstention_rate([1, 1, 1, 1]) == 1.0


def test_rate_zero():
    assert abstention_rate([0, 0, 0]) == 0.0


def test_rate_mixed():
    assert abstention_rate([1, 0, 1, 0, 1]) == 0.6


def test_rate_empty_is_zero():
    assert abstention_rate([]) == 0.0


def test_rate_rounds_to_three_decimals():
    assert abstention_rate([1, 0, 0]) == 0.333
