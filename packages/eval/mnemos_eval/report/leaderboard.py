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

_HEADER = (
    "| " + " | ".join(_COLUMNS) + " |\n"
    + "|" + "|".join(["---"] * len(_COLUMNS)) + "|\n"
)


def append_row(path: Path, row: dict[str, Any]) -> None:
    line = "| " + " | ".join(str(row.get(col, "-")) for col in _COLUMNS) + " |\n"

    if not path.exists():
        path.write_text(_HEADER + line, encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    if not content.lstrip().startswith("|"):
        content = _HEADER + content
    # If schema changed (e.g. v0.5 added new columns), append fresh header before the new row.
    first_line = content.lstrip().split("\n", 1)[0]
    expected_first = _HEADER.split("\n", 1)[0]
    if first_line.strip() != expected_first.strip():
        path.write_text(content.rstrip() + "\n\n" + _HEADER + line, encoding="utf-8")
        return
    path.write_text(content.rstrip() + "\n" + line, encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
