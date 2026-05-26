from mnemos_eval.metrics.precision import precision_at_k


def test_full_precision():
    assert precision_at_k(["a", "b", "c"], ["a", "b", "c"], 3) == 1.0


def test_no_hits():
    assert precision_at_k(["x", "y", "z"], ["a"], 3) == 0.0


def test_partial_precision_top_k():
    assert precision_at_k(["a", "x", "b"], ["a", "b"], 3) == 2 / 3


def test_precision_at_1_top_hit():
    assert precision_at_k(["a", "b"], ["a"], 1) == 1.0


def test_precision_at_1_top_miss():
    assert precision_at_k(["x", "a"], ["a"], 1) == 0.0


def test_k_zero_returns_zero():
    assert precision_at_k(["a"], ["a"], 0) == 0.0


def test_empty_retrieved_returns_zero():
    assert precision_at_k([], ["a"], 5) == 0.0
