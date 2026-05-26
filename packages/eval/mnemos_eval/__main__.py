import json
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.table import Table

from mnemos.config import get_settings

from mnemos_eval.report.leaderboard import (
    append_contradiction_row,
    append_row,
    now_iso,
)
from mnemos_eval.runners.contradiction_runner import run_contradiction_suite
from mnemos_eval.runners.run_suite import _git_sha, run_suite

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


@app.command()
def run(
    dataset: Path = typer.Option(
        Path(__file__).parent / "datasets" / "seed_v0.jsonl",
        "--dataset",
        "-d",
        help="Path to the JSONL dataset.",
    ),
    service_url: str = typer.Option(
        "http://localhost:8000", "--service-url", "-s", help="mnemos service base URL."
    ),
    leaderboard: Path = typer.Option(
        Path.cwd() / "leaderboard.md",
        "--leaderboard",
        "-l",
        help="Path to leaderboard.md to append to.",
    ),
    runs_dir: Path = typer.Option(
        Path.cwd() / "eval-runs",
        "--runs-dir",
        help="Directory to write the full JSON run output.",
    ),
    limit: int = typer.Option(10, "--limit", "-k", help="Top-k retrieved per query."),
    mode: str = typer.Option(
        "dense",
        "--mode",
        "-m",
        help="Search mode: 'dense' or 'hybrid'. Hybrid uses BM25 + dense fused with RRF.",
    ),
) -> None:
    """Run the eval suite, append a leaderboard row, dump the full per-case JSON."""
    if mode not in {"dense", "hybrid"}:
        raise typer.BadParameter("mode must be 'dense' or 'hybrid'")

    settings = get_settings()
    result = run_suite(
        dataset_path=dataset,
        service_url=service_url,
        mode=mode,  # type: ignore[arg-type]
        limit=limit,
        embed_model=settings.embedding_model,
    )

    summary = result["summary"]
    git_sha = _git_sha(Path.cwd())
    summary["git_sha"] = git_sha
    summary["timestamp"] = now_iso()

    runs_dir.mkdir(parents=True, exist_ok=True)
    run_path = (
        runs_dir
        / f"eval_run_{mode}_{git_sha}_{summary['timestamp'].replace(':', '-')}.json"
    )
    run_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    append_row(leaderboard, summary)

    table = Table(
        title=f"mnemos-eval — {summary['dataset']} (mode={mode}, n={summary['n']})"
    )
    for col in [
        "recall@1",
        "recall@5",
        "recall@10",
        "precision@1",
        "precision@5",
        "p50_ms",
        "p95_ms",
    ]:
        table.add_column(col, justify="right")
    table.add_row(
        str(summary["recall@1"]),
        str(summary["recall@5"]),
        str(summary["recall@10"]),
        str(summary["precision@1"]),
        str(summary["precision@5"]),
        str(summary["p50_ms"]),
        str(summary["p95_ms"]),
    )
    console.print(table)
    console.print(f"Wrote leaderboard row to [bold]{leaderboard}[/]")
    console.print(f"Wrote full run to     [bold]{run_path}[/]")


@app.command()
def compare(
    dataset: Path = typer.Option(
        Path(__file__).parent / "datasets" / "seed_v0.jsonl",
        "--dataset",
        "-d",
    ),
    service_url: str = typer.Option("http://localhost:8000", "--service-url", "-s"),
    leaderboard: Path = typer.Option(Path.cwd() / "leaderboard.md", "--leaderboard", "-l"),
    runs_dir: Path = typer.Option(Path.cwd() / "eval-runs", "--runs-dir"),
    limit: int = typer.Option(10, "--limit", "-k"),
) -> None:
    """Run the eval in both modes (dense + hybrid) and append both rows to the leaderboard."""
    for mode in ("dense", "hybrid"):
        run(
            dataset=dataset,
            service_url=service_url,
            leaderboard=leaderboard,
            runs_dir=runs_dir,
            limit=limit,
            mode=mode,
        )


def _run_contradiction(
    dataset: Path,
    service_url: str,
    leaderboard: Path,
    runs_dir: Path,
    judge_kind: str,
) -> dict:
    settings = get_settings()
    judge_model = settings.judge_model if judge_kind == "llm" else settings.nli_model
    result = run_contradiction_suite(
        dataset_path=dataset,
        service_url=service_url,
        judge_model=judge_model,
        judge_kind=judge_kind,
    )

    summary = result["summary"]
    git_sha = _git_sha(Path.cwd())
    summary["git_sha"] = git_sha
    summary["timestamp"] = now_iso()

    runs_dir.mkdir(parents=True, exist_ok=True)
    run_path = (
        runs_dir
        / f"eval_contradiction_{judge_kind}_{git_sha}_{summary['timestamp'].replace(':', '-')}.json"
    )
    run_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    append_contradiction_row(leaderboard, summary)

    table = Table(
        title=f"mnemos-eval contradiction — {summary['dataset']} "
        f"(judge={judge_kind}:{summary['judge_model']}, n={summary['n']})"
    )
    for col in [
        "accuracy",
        "contradiction_f1",
        "contradiction_precision",
        "contradiction_recall",
        "p50_ms",
        "p95_ms",
    ]:
        table.add_column(col, justify="right")
    table.add_row(
        str(summary["accuracy"]),
        str(summary["contradiction_f1"]),
        str(summary["contradiction_precision"]),
        str(summary["contradiction_recall"]),
        str(summary["p50_ms"]),
        str(summary["p95_ms"]),
    )
    console.print(table)
    console.print(f"Wrote leaderboard row to [bold]{leaderboard}[/]")
    console.print(f"Wrote full run to     [bold]{run_path}[/]")
    console.print("Per-class breakdown:")
    for verdict, stats in result["per_class"].items():
        console.print(
            f"  [bold]{verdict}[/]: tp={stats['tp']} fp={stats['fp']} "
            f"fn={stats['fn']} f1={stats['f1']}"
        )
    return summary


@app.command()
def contradiction(
    dataset: Path = typer.Option(
        Path(__file__).parent / "datasets" / "contradiction_v0.jsonl",
        "--dataset",
        "-d",
        help="Path to a JSONL dataset with task_type=contradiction cases.",
    ),
    service_url: str = typer.Option("http://localhost:8000", "--service-url", "-s"),
    leaderboard: Path = typer.Option(Path.cwd() / "leaderboard.md", "--leaderboard", "-l"),
    runs_dir: Path = typer.Option(Path.cwd() / "eval-runs", "--runs-dir"),
    judge: str = typer.Option(
        "llm", "--judge", "-j", help="Judge to use: 'llm' (Claude) or 'nli' (DeBERTa baseline)."
    ),
) -> None:
    """Run a single judge over contradiction pairs, append a leaderboard row."""
    if judge not in {"llm", "nli"}:
        raise typer.BadParameter("--judge must be 'llm' or 'nli'")
    _run_contradiction(dataset, service_url, leaderboard, runs_dir, judge)


@app.command("compare-judges")
def compare_judges(
    dataset: Path = typer.Option(
        Path(__file__).parent / "datasets" / "contradiction_v0.jsonl",
        "--dataset",
        "-d",
    ),
    service_url: str = typer.Option("http://localhost:8000", "--service-url", "-s"),
    leaderboard: Path = typer.Option(Path.cwd() / "leaderboard.md", "--leaderboard", "-l"),
    runs_dir: Path = typer.Option(Path.cwd() / "eval-runs", "--runs-dir"),
) -> None:
    """Run both LLM-judge and NLI baseline on the same dataset, append both rows.

    This is the measurement that justifies the project's defendable claim:
    'we report the gap between a small specialized classifier and a frontier LLM,
    rather than asserting the LLM is correct'.
    """
    summaries = []
    for kind in ("nli", "llm"):
        summaries.append(_run_contradiction(dataset, service_url, leaderboard, runs_dir, kind))

    console.print("\n[bold]Side-by-side[/]")
    cmp_table = Table(title="LLM vs NLI on contradiction_v0")
    cmp_table.add_column("judge")
    cmp_table.add_column("model")
    for col in ["accuracy", "contradiction_f1", "p50_ms"]:
        cmp_table.add_column(col, justify="right")
    for s in summaries:
        cmp_table.add_row(
            s["judge_kind"],
            s["judge_model"],
            str(s["accuracy"]),
            str(s["contradiction_f1"]),
            str(s["p50_ms"]),
        )
    console.print(cmp_table)


if __name__ == "__main__":
    app()
