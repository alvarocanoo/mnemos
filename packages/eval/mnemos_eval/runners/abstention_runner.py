import statistics
import time
from pathlib import Path
from typing import Any, Literal

import httpx

from mnemos_eval.metrics.abstention import abstention_rate, abstention_score
from mnemos_eval.runners.fixtures import load_jsonl

SearchMode = Literal["dense", "hybrid"]
_ENDPOINT_BY_MODE = {"dense": "/search/dense", "hybrid": "/search/hybrid"}


def _ingest_case(client: httpx.Client, case: dict[str, Any]) -> None:
    user_id = f"bench_{case['id']}"
    for mem in case["memories"]:
        resp = client.post(
            "/memories",
            json={
                "content": mem["content"],
                "importance": mem.get("importance", 2),
                "user_id": user_id,
                "metadata": {"bench_case": case["id"]},
            },
            timeout=60.0,
        )
        resp.raise_for_status()


def _query_case(
    client: httpx.Client,
    case: dict[str, Any],
    *,
    mode: SearchMode,
    score_threshold: float,
    limit: int = 10,
) -> tuple[list[str], float]:
    user_id = f"bench_{case['id']}"
    endpoint = _ENDPOINT_BY_MODE[mode]
    t0 = time.perf_counter()
    resp = client.post(
        endpoint,
        json={
            "query": case["query"],
            "user_id": user_id,
            "limit": limit,
            "score_threshold": score_threshold,
        },
        timeout=60.0,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    resp.raise_for_status()
    return [hit["memory"]["id"] for hit in resp.json()], elapsed_ms


def run_abstention_suite(
    dataset_path: Path,
    service_url: str,
    *,
    mode: SearchMode = "hybrid",
    score_threshold: float = 0.0,
    embed_model: str = "BAAI/bge-m3",
) -> dict[str, Any]:
    cases = [c for c in load_jsonl(dataset_path) if c.get("task_type") == "abstention"]
    if not cases:
        raise ValueError(f"No task_type=abstention cases found in {dataset_path}")

    scores: list[int] = []
    latencies_ms: list[float] = []
    per_case: list[dict[str, Any]] = []

    with httpx.Client(base_url=service_url) as client:
        for case in cases:
            _ingest_case(client, case)
            retrieved, latency_ms = _query_case(
                client, case, mode=mode, score_threshold=score_threshold
            )
            score = abstention_score(retrieved)
            scores.append(score)
            latencies_ms.append(latency_ms)
            per_case.append(
                {
                    "id": case["id"],
                    "abstained": bool(score),
                    "n_retrieved": len(retrieved),
                    "latency_ms": round(latency_ms, 2),
                }
            )

    n = len(cases)
    summary = {
        "n": n,
        "dataset": dataset_path.name,
        "mode": mode,
        "embed_model": embed_model,
        "score_threshold": score_threshold,
        "abstention_rate": abstention_rate(scores),
        "p50_ms": round(statistics.median(latencies_ms), 1),
        "p95_ms": round(
            statistics.quantiles(latencies_ms, n=20)[18] if n >= 20 else max(latencies_ms),
            1,
        ),
    }
    return {"summary": summary, "per_case": per_case}
