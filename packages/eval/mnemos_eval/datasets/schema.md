# `mnemos-bench` dataset schema

Each line in `*.jsonl` is one test case. v0.1 ships only `single_hop_recall`; future versions add `multi_session`, `temporal_update`, `contradiction`, `abstention`.

## Common fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable identifier (`shr_001`, `tu_007`, ...) |
| `task_type` | string | `single_hop_recall` for v0.1 |
| `memories` | list of objects | Pool of memories ingested for this case |
| `query` | string | What the agent asks |
| `gold` | object | Ground truth |
| `version` | string | Dataset version this row belongs to |

## `memories[i]` shape

| Field | Type | Notes |
|---|---|---|
| `content` | string | The memory text |
| `importance` | int | 1=low, 2=normal, 3=high (used in v0.5+) |

## `gold` shape for `single_hop_recall`

| Field | Type | Notes |
|---|---|---|
| `memory_indices` | list of int | Indices into `memories[]` that contain the answer |

## Isolation

Each test case is ingested under `user_id = f"bench_{case_id}"` so the search filter never sees other cases' memories. This keeps recall@k clean without per-case database resets.

## Reproducibility

- Each ingest is deterministic (no LLM in v0.1).
- Embeddings depend on `MNEMOS_EMBEDDING_MODEL` (pinned in `eval.config.yaml`).
- Results recorded with `git_sha`, `embed_model`, and dataset SHA in `leaderboard.md`.
