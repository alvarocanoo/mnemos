from collections.abc import Iterable


def precision_at_k(retrieved_ids: list[str], gold_ids: Iterable[str], k: int) -> float:
    """Fraction of the top-k retrieved that are gold.

    Returns 0.0 if k <= 0 or if retrieved is empty.
    """
    if k <= 0 or not retrieved_ids:
        return 0.0
    gold_set = set(gold_ids)
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for r in top_k if r in gold_set)
    return hits / len(top_k)
