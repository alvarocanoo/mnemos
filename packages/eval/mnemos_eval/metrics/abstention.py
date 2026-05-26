from collections.abc import Iterable


def abstention_score(retrieved_ids: list[str]) -> int:
    """1 if the system correctly returned nothing, 0 otherwise.

    Used for cases where the query has no answer in the memory pool and the
    expected behaviour is to abstain rather than return the closest noisy match.
    Soft abstention is achieved upstream via score_threshold on the search call.
    """
    return 1 if len(retrieved_ids) == 0 else 0


def abstention_rate(scores: Iterable[int]) -> float:
    scores_list = list(scores)
    if not scores_list:
        return 0.0
    return round(sum(scores_list) / len(scores_list), 3)
