from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_HEADER = (
    "| timestamp | git_sha | dataset | n | embed_model | recall@1 | recall@5 | recall@10 | p50_ms | p95_ms |\n"
    "|---|---|---|---|---|---|---|---|---|---|\n"
)


def append_row(path: Path, row: dict[str, Any]) -> None:
    line = "| " + " | ".join(
        str(row.get(col, "-"))
        for col in [
            "timestamp",
            "git_sha",
            "dataset",
            "n",
            "embed_model",
            "recall@1",
            "recall@5",
            "recall@10",
            "p50_ms",
            "p95_ms",
        ]
    ) + " |\n"

    if not path.exists():
        path.write_text(_HEADER + line, encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    if not content.lstrip().startswith("|"):
        content = _HEADER + content
    path.write_text(content.rstrip() + "\n" + line, encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
