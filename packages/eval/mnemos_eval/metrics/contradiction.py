from collections.abc import Iterable
from typing import Any

from mnemos.contradiction.types import POSITIVE_VERDICTS, Verdict


def _to_verdict(value: str | Verdict) -> Verdict:
    return value if isinstance(value, Verdict) else Verdict(value)


def collapsed_positive_f1(
    predicted: Iterable[str | Verdict], gold: Iterable[str | Verdict]
) -> dict[str, float]:
    """F1 with {contradicts, supersedes} collapsed as the positive class.

    The other two verdicts (independent, paraphrase) are negatives. Returns
    precision, recall, F1 over the positive class, plus accuracy across all 4
    labels.
    """
    preds = [_to_verdict(p) for p in predicted]
    golds = [_to_verdict(g) for g in gold]
    if len(preds) != len(golds):
        raise ValueError("predicted and gold lengths differ")
    if not preds:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "accuracy": 0.0, "n": 0}

    tp = fp = fn = correct = 0
    for p, g in zip(preds, golds, strict=True):
        p_pos = p in POSITIVE_VERDICTS
        g_pos = g in POSITIVE_VERDICTS
        if p == g:
            correct += 1
        if p_pos and g_pos:
            tp += 1
        elif p_pos and not g_pos:
            fp += 1
        elif not p_pos and g_pos:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = correct / len(preds)
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "accuracy": round(accuracy, 3),
        "n": len(preds),
    }


def per_class_breakdown(
    predicted: Iterable[str | Verdict], gold: Iterable[str | Verdict]
) -> dict[str, dict[str, Any]]:
    """Per-verdict counts (tp/fp/fn) to spot label-specific weaknesses."""
    preds = [_to_verdict(p) for p in predicted]
    golds = [_to_verdict(g) for g in gold]
    out: dict[str, dict[str, Any]] = {}
    for verdict in Verdict:
        tp = sum(1 for p, g in zip(preds, golds, strict=True) if p == verdict and g == verdict)
        fp = sum(1 for p, g in zip(preds, golds, strict=True) if p == verdict and g != verdict)
        fn = sum(1 for p, g in zip(preds, golds, strict=True) if p != verdict and g == verdict)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        out[verdict.value] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }
    return out
