from collections.abc import Iterable


def temporal_consistency_score(
    retrieved_ids: list[str],
    current_id: str,
    superseded_id: str,
    k: int = 5,
) -> int:
    """Returns 1 if the *current* memory ranks above the *superseded* one in top-k.

    Strict interpretation:
      - current must appear in top-k.
      - superseded must NOT appear before current in top-k.
      - If neither appears in top-k, the case is a miss (0).

    Edge case: if current appears and superseded does not, score is 1.
    """
    top_k = retrieved_ids[:k]
    cur_pos = top_k.index(current_id) if current_id in top_k else None
    sup_pos = top_k.index(superseded_id) if superseded_id in top_k else None

    if cur_pos is None:
        return 0
    if sup_pos is None:
        return 1
    return 1 if cur_pos < sup_pos else 0


def aggregate(scores: Iterable[int]) -> float:
    scores_list = list(scores)
    if not scores_list:
        return 0.0
    return round(sum(scores_list) / len(scores_list), 3)
