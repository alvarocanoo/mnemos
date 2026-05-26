import statistics
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import httpx

from mnemos_eval.metrics.temporal import aggregate, temporal_consistency_score
from mnemos_eval.runners.fixtures import load_jsonl


SearchMode = Literal["dense", "hybrid"]
_ENDPOINT_BY_MODE = {"dense": "/search/dense", "hybrid": "/search/hybrid"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ingest_case_with_ages(
    client: httpx.Client, case: dict[str, Any]
) -> list[str]:
    user_id = f"bench_{case['id']}"
    now = _now()
    ids: list[str] = []
    for mem in case["memories"]:
        age_days = float(mem.get("age_days", 0))
        created_at = (now - timedelta(days=age_days)).isoformat()
        resp = client.post(
            "/memories",
            json={
                "content": mem["content"],
                "importance": mem.get("importance", 2),
                "user_id": user_id,
                "metadata": {
                    "bench_case": case["id"],
                    "role": mem.get("role", "memory"),
                    "age_days_at_ingest": age_days,
                },
                "created_at": created_at,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        ids.append(resp.json()["id"])
    return ids


def _query_case(
    client: httpx.Client,
    case: dict[str, Any],
    *,
    mode: SearchMode,
    limit: int = 10,
    apply_decay: bool,
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
            "apply_decay": apply_decay,
        },
        timeout=60.0,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    resp.raise_for_status()
    return [hit["memory"]["id"] for hit in resp.json()], elapsed_ms


def run_temporal_suite(
    dataset_path: Path,
    service_url: str,
    *,
    mode: SearchMode = "hybrid",
    apply_decay: bool = True,
    embed_model: str = "BAAI/bge-m3",
    k: int = 5,
) -> dict[str, Any]:
    cases = load_jsonl(dataset_path)
    cases = [c for c in cases if c.get("task_type") == "temporal_update"]
    if not cases:
        raise ValueError(
            f"No task_type=temporal_update cases found in {dataset_path}"
        )

    scores: list[int] = []
    latencies_ms: list[float] = []
    per_case: list[dict[str, Any]] = []

    with httpx.Client(base_url=service_url) as client:
        for case in cases:
            ingested_ids = _ingest_case_with_ages(client, case)
            current_id = ingested_ids[case["gold"]["current_idx"]]
            superseded_id = ingested_ids[case["gold"]["superseded_idx"]]
            retrieved, latency_ms = _query_case(
                client, case, mode=mode, limit=10, apply_decay=apply_decay
            )
            score = temporal_consistency_score(retrieved, current_id, superseded_id, k=k)
            scores.append(score)
            latencies_ms.append(latency_ms)
            per_case.append(
                {
                    "id": case["id"],
                    "score": score,
                    "current_pos": retrieved.index(current_id) if current_id in retrieved else None,
                    "superseded_pos": retrieved.index(superseded_id) if superseded_id in retrieved else None,
                    "latency_ms": round(latency_ms, 2),
                }
            )

    n = len(cases)
    summary = {
        "n": n,
        "dataset": dataset_path.name,
        "mode": mode,
        "apply_decay": apply_decay,
        "embed_model": embed_model,
        "temporal_consistency": aggregate(scores),
        "p50_ms": round(statistics.median(latencies_ms), 1),
        "p95_ms": round(
            statistics.quantiles(latencies_ms, n=20)[18] if n >= 20 else max(latencies_ms),
            1,
        ),
    }
    return {"summary": summary, "per_case": per_case}
