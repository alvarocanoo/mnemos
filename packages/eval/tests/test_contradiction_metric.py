from mnemos.contradiction.types import Verdict

from mnemos_eval.metrics.contradiction import (
    collapsed_positive_f1,
    per_class_breakdown,
)


def test_collapsed_perfect():
    pred = ["contradicts", "supersedes", "independent", "paraphrase"]
    gold = ["contradicts", "supersedes", "independent", "paraphrase"]
    result = collapsed_positive_f1(pred, gold)
    assert result["f1"] == 1.0
    assert result["accuracy"] == 1.0
    assert result["n"] == 4


def test_collapsed_all_negative_predicted():
    pred = ["independent", "independent", "independent", "independent"]
    gold = ["contradicts", "supersedes", "independent", "paraphrase"]
    result = collapsed_positive_f1(pred, gold)
    assert result["recall"] == 0.0
    assert result["precision"] == 0.0
    assert result["f1"] == 0.0


def test_collapsed_treats_supersedes_as_positive():
    pred = ["supersedes"]
    gold = ["contradicts"]
    result = collapsed_positive_f1(pred, gold)
    assert result["f1"] == 1.0  # both positive after collapse
    assert result["accuracy"] == 0.0  # not the same exact label


def test_collapsed_partial():
    pred = ["contradicts", "contradicts", "independent", "paraphrase"]
    gold = ["contradicts", "independent", "contradicts", "paraphrase"]
    result = collapsed_positive_f1(pred, gold)
    # tp=1 (case 0), fp=1 (case 1), fn=1 (case 2)
    assert result["precision"] == 0.5
    assert result["recall"] == 0.5
    assert result["f1"] == 0.5


def test_accepts_verdict_enum():
    pred = [Verdict.CONTRADICTS, Verdict.PARAPHRASE]
    gold = ["contradicts", "paraphrase"]
    result = collapsed_positive_f1(pred, gold)
    assert result["f1"] == 1.0


def test_length_mismatch_raises():
    import pytest

    with pytest.raises(ValueError):
        collapsed_positive_f1(["contradicts"], ["contradicts", "supersedes"])


def test_per_class_breakdown_keys():
    pred = ["contradicts", "supersedes", "independent", "paraphrase"]
    gold = ["contradicts", "supersedes", "independent", "paraphrase"]
    bd = per_class_breakdown(pred, gold)
    assert set(bd.keys()) == {"contradicts", "supersedes", "independent", "paraphrase"}
    for verdict_stats in bd.values():
        assert verdict_stats["f1"] == 1.0
        assert verdict_stats["fp"] == 0
        assert verdict_stats["fn"] == 0
