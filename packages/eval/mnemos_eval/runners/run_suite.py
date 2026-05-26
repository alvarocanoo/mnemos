import statistics
import subprocess
import time
from pathlib import Path
from typing import Any, Literal

import httpx

from mnemos_eval.metrics.precision import precision_at_k
from mnemos_eval.metrics.recall import recall_at_k
from mnemos_eval.runners.fixtures import load_jsonl

SearchMode = Literal["dense", "hybrid"]


def _git_sha(cwd: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=cwd, text=True
        ).strip()
    except Exception:
        return "unknown"


def _ingest_case(client: httpx.Client, case: dict[str, Any]) -> list[str]:
    """Ingest memories for one case under a unique user_id; return the resulting memory ids in order."""
    user_id = f"bench_{case['id']}"
    ids: list[str] = []
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
        ids.append(resp.json()["id"])
    return ids


def _query_case(
    client: httpx.Client,
    case: dict[str, Any],
    *,
    mode: SearchMode,
    limit: int = 10,
) -> tuple[list[str], float]:
    user_id = f"bench_{case['id']}"
    endpoint = "/search/dense" if mode == "dense" else "/search/hybrid"
    t0 = time.perf_counter()
    resp = client.post(
        endpoint,
        json={"query": case["query"], "user_id": user_id, "limit": limit},
        timeout=60.0,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    resp.raise_for_status()
    hits = resp.json()
    return [hit["memory"]["id"] for hit in hits], elapsed_ms


def run_suite(
    dataset_path: Path,
    service_url: str,
    *,
    mode: SearchMode = "dense",
    limit: int = 10,
    embed_model: str = "BAAI/bge-m3",
) -> dict[str, Any]:
    cases = load_jsonl(dataset_path)
    if not cases:
        raise ValueError(f"Dataset {dataset_path} is empty")

    recalls_1: list[float] = []
    recalls_5: list[float] = []
    recalls_10: list[float] = []
    precisions_1: list[float] = []
    precisions_5: list[float] = []
    latencies_ms: list[float] = []
    per_case: list[dict[str, Any]] = []

    with httpx.Client(base_url=service_url) as client:
        for case in cases:
            ingested_ids = _ingest_case(client, case)
            gold_ids = [ingested_ids[i] for i in case["gold"]["memory_indices"]]
            retrieved_ids, latency_ms = _query_case(client, case, mode=mode, limit=limit)

            r1 = recall_at_k(retrieved_ids, gold_ids, 1)
            r5 = recall_at_k(retrieved_ids, gold_ids, 5)
            r10 = recall_at_k(retrieved_ids, gold_ids, 10)
            p1 = precision_at_k(retrieved_ids, gold_ids, 1)
            p5 = precision_at_k(retrieved_ids, gold_ids, 5)
            recalls_1.append(r1)
            recalls_5.append(r5)
            recalls_10.append(r10)
            precisions_1.append(p1)
            precisions_5.append(p5)
            latencies_ms.append(latency_ms)

            per_case.append(
                {
                    "id": case["id"],
                    "task_type": case["task_type"],
                    "recall@1": r1,
                    "recall@5": r5,
                    "recall@10": r10,
                    "precision@1": p1,
                    "precision@5": p5,
                    "latency_ms": round(latency_ms, 2),
                }
            )

    n = len(cases)
    summary = {
        "n": n,
        "dataset": dataset_path.name,
        "mode": mode,
        "embed_model": embed_model,
        "recall@1": round(sum(recalls_1) / n, 3),
        "recall@5": round(sum(recalls_5) / n, 3),
        "recall@10": round(sum(recalls_10) / n, 3),
        "precision@1": round(sum(precisions_1) / n, 3),
        "precision@5": round(sum(precisions_5) / n, 3),
        "p50_ms": round(statistics.median(latencies_ms), 1),
        "p95_ms": round(
            statistics.quantiles(latencies_ms, n=20)[18] if n >= 20 else max(latencies_ms),
            1,
        ),
    }
    return {"summary": summary, "per_case": per_case}
