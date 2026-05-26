from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_COLUMNS = [
    "timestamp",
    "git_sha",
    "dataset",
    "mode",
    "n",
    "embed_model",
    "recall@1",
    "recall@5",
    "recall@10",
    "precision@1",
    "precision@5",
    "p50_ms",
    "p95_ms",
]

_TEMPORAL_COLUMNS = [
    "timestamp",
    "git_sha",
    "dataset",
    "mode",
    "apply_decay",
    "n",
    "embed_model",
    "temporal_consistency",
    "p50_ms",
    "p95_ms",
]

_ABSTENTION_COLUMNS = [
    "timestamp",
    "git_sha",
    "dataset",
    "mode",
    "score_threshold",
    "n",
    "embed_model",
    "abstention_rate",
    "p50_ms",
    "p95_ms",
]

_CONTRADICTION_COLUMNS = [
    "timestamp",
    "git_sha",
    "dataset",
    "n",
    "judge_kind",
    "judge_model",
    "accuracy",
    "contradiction_f1",
    "contradiction_precision",
    "contradiction_recall",
    "p50_ms",
    "p95_ms",
]

def _make_header(columns: list[str]) -> str:
    return (
        "| " + " | ".join(columns) + " |\n"
        + "|" + "|".join(["---"] * len(columns)) + "|\n"
    )


_HEADER = _make_header(_COLUMNS)
_CONTRADICTION_HEADER = _make_header(_CONTRADICTION_COLUMNS)
_TEMPORAL_HEADER = _make_header(_TEMPORAL_COLUMNS)
_ABSTENTION_HEADER = _make_header(_ABSTENTION_COLUMNS)


def _append_with_schema(path: Path, columns: list[str], header: str, row: dict[str, Any]) -> None:
    line = "| " + " | ".join(str(row.get(col, "-")) for col in columns) + " |\n"

    if not path.exists():
        path.write_text(header + line, encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    if not content.lstrip().startswith("|"):
        content = header + content

    expected_first = header.split("\n", 1)[0].strip()
    # Find the last header in the file (so multiple schemas can coexist as separate blocks)
    last_header_seen: str | None = None
    for line_text in content.splitlines():
        if line_text.startswith("|") and "---" not in line_text and "|" in line_text[1:]:
            last_header_seen = line_text.strip()

    if last_header_seen != expected_first:
        path.write_text(content.rstrip() + "\n\n" + header + line, encoding="utf-8")
        return
    path.write_text(content.rstrip() + "\n" + line, encoding="utf-8")


def append_row(path: Path, row: dict[str, Any]) -> None:
    _append_with_schema(path, _COLUMNS, _HEADER, row)


def append_contradiction_row(path: Path, row: dict[str, Any]) -> None:
    _append_with_schema(path, _CONTRADICTION_COLUMNS, _CONTRADICTION_HEADER, row)


def append_temporal_row(path: Path, row: dict[str, Any]) -> None:
    _append_with_schema(path, _TEMPORAL_COLUMNS, _TEMPORAL_HEADER, row)


def append_abstention_row(path: Path, row: dict[str, Any]) -> None:
    _append_with_schema(path, _ABSTENTION_COLUMNS, _ABSTENTION_HEADER, row)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
