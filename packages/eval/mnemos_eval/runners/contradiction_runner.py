import statistics
import time
from pathlib import Path
from typing import Any

import httpx

from mnemos_eval.metrics.contradiction import collapsed_positive_f1, per_class_breakdown
from mnemos_eval.runners.fixtures import load_jsonl


def _call_judge(client: httpx.Client, case: dict[str, Any]) -> tuple[str, float]:
    t0 = time.perf_counter()
    resp = client.post(
        "/contradiction/detect",
        json={"memory_a": case["memory_a"], "memory_b": case["memory_b"]},
        timeout=120.0,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    resp.raise_for_status()
    return resp.json()["verdict"], elapsed_ms


def run_contradiction_suite(
    dataset_path: Path,
    service_url: str,
    *,
    judge_model: str = "claude-haiku-4-5",
) -> dict[str, Any]:
    cases = load_jsonl(dataset_path)
    if not cases:
        raise ValueError(f"Dataset {dataset_path} is empty")

    predicted: list[str] = []
    gold: list[str] = []
    latencies_ms: list[float] = []
    per_case: list[dict[str, Any]] = []

    with httpx.Client(base_url=service_url) as client:
        for case in cases:
            if case.get("task_type") != "contradiction":
                continue
            verdict, latency_ms = _call_judge(client, case)
            gold_verdict = case["gold"]["verdict"]
            predicted.append(verdict)
            gold.append(gold_verdict)
            latencies_ms.append(latency_ms)
            per_case.append(
                {
                    "id": case["id"],
                    "predicted": verdict,
                    "gold": gold_verdict,
                    "correct": verdict == gold_verdict,
                    "latency_ms": round(latency_ms, 2),
                }
            )

    if not predicted:
        raise ValueError(
            f"No task_type=contradiction cases found in {dataset_path}"
        )

    collapsed = collapsed_positive_f1(predicted, gold)
    per_class = per_class_breakdown(predicted, gold)
    n = len(predicted)
    summary = {
        "n": n,
        "dataset": dataset_path.name,
        "task_type": "contradiction",
        "judge_model": judge_model,
        "accuracy": collapsed["accuracy"],
        "contradiction_f1": collapsed["f1"],
        "contradiction_precision": collapsed["precision"],
        "contradiction_recall": collapsed["recall"],
        "p50_ms": round(statistics.median(latencies_ms), 1),
        "p95_ms": round(
            statistics.quantiles(latencies_ms, n=20)[18] if n >= 20 else max(latencies_ms),
            1,
        ),
    }
    return {"summary": summary, "per_case": per_case, "per_class": per_class}
