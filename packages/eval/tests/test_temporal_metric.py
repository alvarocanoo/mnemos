from mnemos_eval.metrics.temporal import aggregate, temporal_consistency_score


def test_current_ranked_above_superseded():
    retrieved = ["cur", "sup", "x", "y", "z"]
    assert temporal_consistency_score(retrieved, "cur", "sup") == 1


def test_superseded_ranked_above_current():
    retrieved = ["sup", "cur", "x", "y", "z"]
    assert temporal_consistency_score(retrieved, "cur", "sup") == 0


def test_only_current_in_top_k():
    retrieved = ["cur", "x", "y", "z", "w"]
    assert temporal_consistency_score(retrieved, "cur", "sup") == 1


def test_neither_in_top_k_is_zero():
    retrieved = ["a", "b", "c", "d", "e"]
    assert temporal_consistency_score(retrieved, "cur", "sup") == 0


def test_only_superseded_in_top_k_is_zero():
    retrieved = ["sup", "x", "y", "z", "w"]
    assert temporal_consistency_score(retrieved, "cur", "sup") == 0


def test_window_k_truncates():
    retrieved = ["a", "b", "c", "d", "e", "cur", "sup"]
    assert temporal_consistency_score(retrieved, "cur", "sup", k=5) == 0
    assert temporal_consistency_score(retrieved, "cur", "sup", k=10) == 1


def test_aggregate_average():
    assert aggregate([1, 1, 0, 1, 0]) == 0.6


def test_aggregate_empty_is_zero():
    assert aggregate([]) == 0.0
