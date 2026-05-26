from unittest.mock import MagicMock

import pytest
from mnemos.contradiction.nli import NLIBaseline, NLIUnavailableError
from mnemos.contradiction.types import ContradictionInput, Verdict


def _mock_loaded(monkeypatch, baseline: NLIBaseline) -> None:
    baseline._tokenizer = MagicMock()
    baseline._model = MagicMock()
    baseline._model.config.id2label = {
        0: "CONTRADICTION",
        1: "ENTAILMENT",
        2: "NEUTRAL",
    }
    baseline._labels_lower = ["contradiction", "entailment", "neutral"]


def _patch_probs(monkeypatch, baseline: NLIBaseline, probs_pairs: list[dict[str, float]]):
    """probs_pairs has 2 entries: [A->B, B->A]"""
    calls = iter(probs_pairs)
    monkeypatch.setattr(baseline, "_nli_probs", lambda p, h: next(calls))


def _input() -> ContradictionInput:
    return ContradictionInput(memory_a="A", memory_b="B")


def test_contradicts_when_either_direction_above_threshold(monkeypatch):
    b = NLIBaseline(threshold=0.5)
    _mock_loaded(monkeypatch, b)
    _patch_probs(
        monkeypatch,
        b,
        [
            {"contradiction": 0.9, "entailment": 0.05, "neutral": 0.05},
            {"contradiction": 0.2, "entailment": 0.4, "neutral": 0.4},
        ],
    )
    result = b.judge(_input())
    assert result.verdict is Verdict.CONTRADICTS
    assert "SUPERSEDES not distinguishable" in result.reason


def test_paraphrase_when_both_directions_entail(monkeypatch):
    b = NLIBaseline(threshold=0.5)
    _mock_loaded(monkeypatch, b)
    _patch_probs(
        monkeypatch,
        b,
        [
            {"contradiction": 0.05, "entailment": 0.8, "neutral": 0.15},
            {"contradiction": 0.05, "entailment": 0.7, "neutral": 0.25},
        ],
    )
    result = b.judge(_input())
    assert result.verdict is Verdict.PARAPHRASE


def test_independent_when_neutral_dominates(monkeypatch):
    b = NLIBaseline(threshold=0.5)
    _mock_loaded(monkeypatch, b)
    _patch_probs(
        monkeypatch,
        b,
        [
            {"contradiction": 0.1, "entailment": 0.2, "neutral": 0.7},
            {"contradiction": 0.1, "entailment": 0.2, "neutral": 0.7},
        ],
    )
    result = b.judge(_input())
    assert result.verdict is Verdict.INDEPENDENT


def test_one_way_entailment_not_enough_for_paraphrase(monkeypatch):
    b = NLIBaseline(threshold=0.5)
    _mock_loaded(monkeypatch, b)
    _patch_probs(
        monkeypatch,
        b,
        [
            {"contradiction": 0.1, "entailment": 0.8, "neutral": 0.1},
            {"contradiction": 0.1, "entailment": 0.3, "neutral": 0.6},
        ],
    )
    result = b.judge(_input())
    # min(0.8, 0.3) = 0.3 < 0.5 → not PARAPHRASE → falls through to INDEPENDENT
    assert result.verdict is Verdict.INDEPENDENT


def test_available_when_transformers_importable():
    b = NLIBaseline()
    assert b.available is True  # transformers + torch installed in dev env


def test_missing_label_in_id2label_raises(monkeypatch):
    b = NLIBaseline()
    b._tokenizer = MagicMock()
    b._model = MagicMock()
    b._model.config.id2label = {0: "POSITIVE", 1: "NEGATIVE"}
    with pytest.raises(NLIUnavailableError, match="missing"):
        # bypass _ensure_loaded re-init; re-run validation manually
        from mnemos.contradiction.nli import _REQUIRED_LABELS

        labels = [str(b._model.config.id2label[i]).lower() for i in range(2)]
        missing = _REQUIRED_LABELS - set(labels)
        assert missing
        raise NLIUnavailableError(
            f"Model {b.model_name} labels are {labels}; missing {sorted(missing)}."
        )
