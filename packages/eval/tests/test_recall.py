from mnemos_eval.metrics.recall import recall_at_k


def test_full_hit_at_k():
    assert recall_at_k(["a", "b", "c"], ["a"], 1) == 1.0


def test_miss_at_k():
    assert recall_at_k(["b", "c", "d"], ["a"], 5) == 0.0


def test_partial_recall_two_gold():
    assert recall_at_k(["a", "x", "y"], ["a", "b"], 5) == 0.5


def test_k_smaller_than_gold_position():
    assert recall_at_k(["x", "a"], ["a"], 1) == 0.0
    assert recall_at_k(["x", "a"], ["a"], 2) == 1.0


def test_empty_gold_returns_zero():
    assert recall_at_k(["a", "b"], [], 5) == 0.0


def test_empty_retrieved_with_gold_returns_zero():
    assert recall_at_k([], ["a"], 5) == 0.0
