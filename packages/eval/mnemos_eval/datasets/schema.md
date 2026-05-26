# `mnemos-bench` dataset schema

Each line in `*.jsonl` is one test case. v1 ships all five task types:

| task_type | runner | metric | file |
|---|---|---|---|
| `single_hop_recall` | `mnemos-eval run` | recall@k, precision@k | `seed_v0.jsonl` (20) |
| `multi_session_reasoning` | `mnemos-eval run` | recall@k, precision@k | `multi_session_v0.jsonl` (15) |
| `contradiction` | `mnemos-eval contradiction` | F1 vs gold verdict | `contradiction_v0.jsonl` (15) |
| `temporal_update` | `mnemos-eval temporal` | temporal_consistency | `temporal_v0.jsonl` (10) |
| `abstention` | `mnemos-eval abstention` | abstention_rate | `abstention_v0.jsonl` (15) |

The five files concatenate into [`mnemos_bench_v1.jsonl`](mnemos_bench_v1.jsonl) (75 cases total). Each runner filters by `task_type`, so you can point any runner at the combined file or at the per-type file.

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

## `gold` shape for `single_hop_recall` and `multi_session_reasoning`

| Field | Type | Notes |
|---|---|---|
| `memory_indices` | list of int | Indices into `memories[]` that contain the answer |

## `gold` shape for `contradiction`

Top-level uses `memory_a` and `memory_b` (strings) instead of a `memories[]` list.

| Field | Type | Notes |
|---|---|---|
| `verdict` | `contradicts` / `supersedes` / `independent` / `paraphrase` | Ground truth verdict |

## `gold` shape for `temporal_update`

`memories[i]` carries an extra `age_days` (number) and `role` (`current` / `superseded` / `distractor`).

| Field | Type | Notes |
|---|---|---|
| `current_idx` | int | Index of the current-truth memory |
| `superseded_idx` | int | Index of the outdated one |

## `gold` shape for `abstention`

| Field | Type | Notes |
|---|---|---|
| `memory_indices` | empty list `[]` | No memory should be returned |
| `expected_empty` | `true` | Explicit flag for readability |

## Isolation

Each test case is ingested under `user_id = f"bench_{case_id}"` so the search filter never sees other cases' memories. This keeps recall@k clean without per-case database resets.

## Reproducibility

- Each ingest is deterministic (no LLM in v0.1).
- Embeddings depend on `MNEMOS_EMBEDDING_MODEL` (pinned in `eval.config.yaml`).
- Results recorded with `git_sha`, `embed_model`, and dataset SHA in `leaderboard.md`.
