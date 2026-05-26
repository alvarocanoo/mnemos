from collections.abc import Iterable


def recall_at_k(retrieved_ids: list[str], gold_ids: Iterable[str], k: int) -> float:
    """Fraction of gold ids present in the first `k` retrieved ids.

    Returns 0.0 if `gold_ids` is empty (no signal to measure).
    """
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0
    top_k = set(retrieved_ids[:k])
    return len(gold_set & top_k) / len(gold_set)
