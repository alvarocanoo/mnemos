# Changelog

All notable changes to `mnemos` are documented in this file. The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The version line of each entry reflects the *intended* git tag. Tags will be created when the first real `leaderboard.md` row lands; until then `Unreleased` is the live branch.

## [Unreleased]

### Added
- GitHub Actions CI workflow: `ruff check`, `ruff format --check`, `pytest`, and a separate `next build` job for the dashboard.
- README badges for CI status, license, and Python version.
- `.github/pull_request_template.md`: minimal contributor checklist mirroring CI.
- `CONTRIBUTING.md`: setup, where each kind of change goes, dataset hand-authoring preference, rule that upstream claims go to `VERIFIED.md`.
- `.env.example`: every `MNEMOS_*` variable documented with its default and what it does.
- `CHANGELOG.md` (this file).
- `.pre-commit-config.yaml`: runs ruff check + format before each commit so the CI rule "everything ruff-clean" is enforced locally too.

### Changed
- Ruff configuration tightened with documented global ignores (`S101`, `B008`, `S607`) and one per-file ignore (`S311` on `fixtures.py`). 87 → 0 lint errors; 57 files re-formatted by `ruff format`. All 71 tests still pass.

## [0.5.0] — 2026-05-26

The first feature-complete iteration. Backend ships the four pillars promised in the project plan; the eval framework ships its own versioned benchmark.

### Added
- **Hybrid retrieval.** Qdrant `Prefetch` + `FusionQuery(Fusion.RRF)` over BGE-M3 dense + `Qdrant/bm25` sparse vectors written in the same upsert. `POST /search/hybrid`, `mnemos-eval compare` (dense vs hybrid).
- **Contradiction detection — LLM judge.** Claude Haiku 4.5 via Anthropic SDK with forced `tool_use` returning structured `{verdict, reason}`. Four verdicts: `contradicts`, `supersedes`, `independent`, `paraphrase`. `POST /contradiction/detect`, `mnemos-eval contradiction --judge llm`.
- **Contradiction detection — NLI baseline.** `cross-encoder/nli-deberta-v3-base` bidirectional via transformers + torch (CPU). `id2label` validated at load time. `POST /contradiction/baseline`, `mnemos-eval contradiction --judge nli`, `mnemos-eval compare-judges` for the LLM-vs-NLI gap.
- **Temporal decay.** `w(t) = exp(-λ_i · Δt_days)` per importance tier. Applied post-Qdrant: overfetch 3×, multiply, re-rank, truncate. `MemoryWrite.created_at` is an eval-only override so `temporal_update` cases can simulate aged memories. `mnemos-eval temporal`, `compare-decay`.
- **Importance-weighted eviction.** Composite score `w_I·importance + w_R·decay_weight(age) + w_A·log1p(access_count)`. `POST /memories/score-eviction` (dry-run) and `POST /memories/evict` (Postgres delete → Qdrant bulk delete, idempotent, no orphan vectors on SQL failure).
- **`mnemos-bench-v1` dataset.** 75 hand-authored cases across five task types: `single_hop_recall` (20), `multi_session_reasoning` (15), `contradiction` (15), `temporal_update` (10), `abstention` (15). Per-task `gold` shapes documented in [`schema.md`](packages/eval/mnemos_eval/datasets/schema.md). Combined into `mnemos_bench_v1.jsonl` via `make bench-build`.
- **Metrics.** `recall@k`, `precision@k`, `collapsed_positive_f1` + `per_class_breakdown` for contradiction, `temporal_consistency`, `abstention_rate`.
- **Soft abstention.** `SearchQuery.score_threshold` filters retrieval hits below a configurable score so the system can return `[]` instead of the closest noisy match.
- **Next.js 16 read-only dashboard.** Server components only, Tailwind 4 CSS-first. Pages: `/memories`, `/eval` (parses mounted `leaderboard.md`), `/timeline` (bars sized by eviction score). Joined `docker-compose` on `:3000`.
- **License.** Apache-2.0, with SPDX expressions in every `pyproject.toml` and `package.json`.
- **README** rewritten as paper-light (~2800 words): abstract, problem, architecture diagram, eval methodology, results table structure, comparison with related work, limitations.
- **Letta column in the comparison table** populated from the upstream source at [`letta-ai/letta@main`](https://github.com/letta-ai/letta) rather than from marketing docs. Every cell links to the file the verdict came from.
- **First blog post** (ES + EN): *"I wrote the eval suite before I wrote the memory system"*.

### Changed
- Leaderboard `append_row` now coexists with three additional schema blocks (`_CONTRADICTION_COLUMNS`, `_TEMPORAL_COLUMNS`, `_ABSTENTION_COLUMNS`); each is a separate markdown table inside the same `leaderboard.md`.
- `run_suite` accepts both `single_hop_recall` and `multi_session_reasoning` as retrieval task types so `mnemos-eval run` works against either per-type file or the combined bench.

## [0.1.0] — 2026-05-26

Skeleton. Enough to demo `ingest → search → eval` end-to-end with a tiny dataset.

### Added
- `uv` workspace scaffolding: `packages/core`, `packages/service`, `packages/eval`. Each is independently installable; the root pins them via `[tool.uv.sources] workspace = true`.
- Postgres schema (`memories` table with importance, metadata JSONB, access counts, timestamps, indices) shipped as alembic migration `0001_initial`.
- Qdrant client wrapper that creates the collection with both dense **and** sparse vector slots from day one — v0.5 adds BM25 ingest without recreating the collection.
- Lazy-loaded `DenseEmbedder` for BGE-M3 via `fastembed`.
- FastAPI service: `/healthz`, `/readyz`, `POST /memories`, `GET /memories/{id}`, `GET /memories`, `DELETE /memories/{id}`, `POST /search/dense`.
- `mnemos-eval run` CLI (`typer`): ingests a JSONL dataset case-by-case under isolated `user_id`s, queries `/search/dense`, computes `recall@1/5/10`, appends a leaderboard row + writes per-case JSON to `eval-runs/`.
- 20-case `seed_v0.jsonl` (`single_hop_recall`).
- `docker-compose` stack (`postgres` + `qdrant` + `service`), multi-stage `Dockerfile` with `uv` build cache layer, healthchecks.
- `Makefile` targets: `sync`, `up`, `down`, `logs`, `verify-stack`, `seed`, `eval`, `test`, `lint`.
- `VERIFIED.md`: week-zero verification log for every external claim that lands in the README.
- `ARCHITECTURE.md`: module-level layout, decision rationale per component, alternatives considered.
- 10 unit tests (recall metric edge cases, Pydantic model bounds).

## Notes

This project's first three "version" tags collapse into the same calendar day (`2026-05-26`) because development happened in a deliberate one-session burst. The version numbers reflect functional milestones (v0.1 = walking skeleton, v0.5 = feature-complete backend + dataset, v1.0 = real leaderboard + writeup, planned) rather than calendar time. See `git log` for the actual commit cadence.
