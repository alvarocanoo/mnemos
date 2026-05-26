# mnemos

> Agent memory system with a public, reproducible evaluation framework.
> Hybrid retrieval, contradiction detection (LLM judge + NLI baseline), configurable temporal decay, importance-weighted eviction — all measurable from `make eval`.

**Status**: v0.5 backend complete + `mnemos-bench-v1` shipped (75 hand-authored cases across 5 task types). Pending for v1.0: first real leaderboard run on author hardware, two blog posts. The repository is feature-complete; what remains is *measurement and writeup*.

- 75 cases · 5 task types · 4 leaderboard schemas
- 71 unit tests pass in ~10 s
- One command (`docker compose up`) reproduces the entire stack
- One command (`make eval-compare`) appends a leaderboard row from a fresh clone

---

## Abstract

Most agent-memory systems claim "works well" without publishing a dataset, a baseline, or a way to reproduce their numbers. `mnemos` exists to make the behaviour of an agent-memory system **measurable and tunable** by anyone with Docker. It is a reference implementation — hybrid retrieval, contradiction detection, temporal decay, importance-weighted eviction — shipped *together with* its own benchmark (`mnemos-bench-v1`), its evaluation harness (`mnemos-eval`), and a Next.js dashboard that renders the live state and the leaderboard. The defendable claim is narrow and verifiable: **`mnemos` is the only system in this comparison that ships a versioned eval dataset, a configurable temporal-decay function, and a one-command reproducible local eval pipeline**.

---

## The problem

Long-term agent memory is a hot subfield in 2026 (Mem0, Zep/Graphiti, Letta, MemGPT, and the LongMemEval benchmark all landed in the last 18 months). Yet portfolio-level work in the area still tends to follow one of three patterns:

1. A wrapper around someone else's memory framework with a fresh `README`.
2. A multi-agent demo where memory exists but is never measured.
3. A blog post claiming X works without any number, dataset, or comparison.

The gap isn't memory algorithms — it is **measurement infrastructure**. Hiring managers in the AI-engineer market consistently flag "eval design rigor" as the strongest single signal of real LLM experience [Anthropic FDE spec, May 2026; DigitalApplied, May 2026]. The market is saturated with chatbots; it is not saturated with people who designed an eval suite *before* writing the system it scores.

`mnemos` is built around that thesis. The eval framework is not a test harness added at the end. It is the product.

---

## System architecture

```
                       +----------------+
                       |  Next.js 16    |
                       |  dashboard     |  :3000
                       |  (read-only)   |
                       +--------+-------+
                                | HTTP (server components)
                                v
                       +----------------+
                       |  FastAPI       |  :8000
                       |  service       |
                       |                |
                       |  /memories     |
                       |  /search/*     |
                       |  /contradiction|
                       |  /memories/evict
                       +-+------------+-+
                  SQL    |            |   HTTP
                         v            v
                  +-------------+  +-------------+
                  |  Postgres   |  |  Qdrant     |
                  |  :5432      |  |  :6333      |
                  |             |  |             |
                  | memories    |  | dense (M3)  |
                  | + metadata  |  | sparse(BM25)|
                  +-------------+  +-------------+
                         ^               ^
                         |  upserts both vectors
                         |  in one call
                         +------+--------+
                                |
                       (mnemos-core library:
                        embeddings + ops + retrieval
                        + decay + eviction + judge)
```

Storage is intentionally split:

| Data | Store | Why |
|---|---|---|
| Memory text, importance, timestamps, access counts, eval runs | Postgres | Transactional updates (decay job, eviction, access bumps), SQL filters, auditable |
| Dense embedding (1024-d, BGE-M3) | Qdrant | Native ANN, payload filters, hybrid fusion |
| Sparse vector (BM25-style) | Qdrant sparse vectors | Verified Qdrant-native; one store, one query |
| LLM judge calls | Anthropic API (Claude Haiku 4.5) | Forced tool-use returns structured JSON, no parsing |
| NLI baseline | Local transformers + torch | DeBERTa-v3 bidirectional, no API key required |

No graph database. Entities-as-relational-rows are enough at this scale and stay defendable in interview without invoking Neo4j or Graphiti.

See [ARCHITECTURE.md](ARCHITECTURE.md) for module-level paths, decision rationale per component, and the alternatives that were considered for each.

---

## Eval methodology

`mnemos-bench-v1` is a hand-authored, English-only, 75-case benchmark. Each case is one line of JSON ([schema](packages/eval/mnemos_eval/datasets/schema.md)):

| Task type | Cases | What it measures | Metric |
|---|---|---|---|
| `single_hop_recall` | 20 | A fact stated once is retrievable when asked directly | recall@1 / @5 / @10, precision@1 / @5 |
| `multi_session_reasoning` | 15 | A query whose answer requires combining facts from 2+ "sessions" | same |
| `contradiction` | 15 | Pairs of memories labelled as `contradicts` / `supersedes` / `independent` / `paraphrase` | F1 with `{contradicts, supersedes}` collapsed positive |
| `temporal_update` | 10 | A current-truth memory exists alongside a superseded one | `temporal_consistency`: fraction where current ranks above superseded in top-5 |
| `abstention` | 15 | Query whose answer is *not* in the memory pool | `abstention_rate`: fraction where the system returns `[]` |
| **TOTAL** | **75** | | 4 leaderboard schemas |

### Reproducibility commitments

- Seeded fixtures (`random.Random(42)`) so case order is deterministic per run.
- The dataset is committed and versioned; every leaderboard row records its git SHA + the file's content SHA implicitly via the SHA pin.
- Embedding model + LLM judge model pinned via env (`MNEMOS_EMBEDDING_MODEL`, `MNEMOS_JUDGE_MODEL`).
- One command per eval — no notebooks, no manual setup, no "first run is different".
- Per-case JSON output (`eval-runs/eval_*.json`) so individual misses can be replayed without re-running the suite.

### Judge methodology

Contradiction detection is reported in **two** flavours, side by side:

1. **LLM judge** — Claude Haiku 4.5 with [forced tool_use](https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview), `tool_choice={"type":"tool","name":"report_verdict"}`. The output is always a structured `{verdict, reason}` object — no free-text parsing.
2. **NLI baseline** — `cross-encoder/nli-deberta-v3-base`, bidirectional (premise→hypothesis and the reverse), takes max contradiction probability and min entailment. Reads `id2label` from the model config at load time so it does not silently misinterpret label order if the model is swapped.

The framework deliberately ships both because *the comparison is the contribution*. `mnemos-eval compare-judges` runs both back-to-back and prints the gap. A future write-up will report numbers like "LLM judge F1 = 0.X, NLI baseline F1 = 0.Y on the same 15 pairs" rather than asserting "the LLM is correct" without evidence.

### Decay methodology

Temporal decay is applied **post-Qdrant**, not pre. Qdrant ranks by similarity; the retriever overfetches 3× the requested top-k, multiplies each score by `exp(-λ_i · Δt_days)`, re-sorts, and truncates. Lambda is per importance tier with intuitive half-lives — `low (λ=0.05) → 14 days`, `normal (λ=0.02) → 35 days`, `high (λ=0.005) → 140 days`. These defaults are starting points to be tuned via `compare-decay`.

The temporal dataset simulates ages by passing `created_at` (offset from now) at ingest time. `MemoryWrite.created_at` is documented as an eval-only override; production callers should leave it `None` so the database default wins.

---

## Results — pending the first real run

The leaderboard tables below show the **structure** that `mnemos-eval` writes. The numeric rows are populated on author hardware (a Docker setup is required, and the first BGE-M3 download is ~700 MB). To produce them, after `make up`:

```powershell
make eval               # single-hop, hybrid mode, decay on
make eval-multi         # multi-session
make eval-compare       # dense vs hybrid side by side
make eval-compare-judges      # LLM judge vs NLI baseline
make eval-compare-decay       # decay OFF vs ON
make eval-abstention          # soft abstention via score_threshold
Get-Content leaderboard.md
```

### Retrieval block

```
| timestamp | git_sha | dataset | mode | n | embed_model | recall@1 | recall@5 | recall@10 | precision@1 | precision@5 | p50_ms | p95_ms |
|-----------|---------|---------|------|---|-------------|----------|----------|-----------|-------------|-------------|--------|--------|
| pending   | bench_v1 | seed_v0 | dense  | 20 | BAAI/bge-m3 | ?        | ?        | ?         | ?           | ?           | ?      | ?      |
| pending   | bench_v1 | seed_v0 | hybrid | 20 | BAAI/bge-m3 | ?        | ?        | ?         | ?           | ?           | ?      | ?      |
| pending   | bench_v1 | multi_session_v0 | hybrid | 15 | BAAI/bge-m3 | ? | ? | ? | ? | ? | ? | ? |
```

### Contradiction block

```
| dataset | n | judge_kind | judge_model | accuracy | f1 | precision | recall | p50_ms | p95_ms |
|---------|---|-----------|-----------------------|----------|----|-----------|--------|--------|--------|
| contradiction_v0 | 15 | nli | cross-encoder/nli-deberta-v3-base | ? | ? | ? | ? | ? | ? |
| contradiction_v0 | 15 | llm | claude-haiku-4-5 | ? | ? | ? | ? | ? | ? |
```

The interesting row is the **gap** between the two — the contribution is "we measured it", not "the LLM was right".

### Temporal block

```
| dataset | mode | apply_decay | n | embed_model | temporal_consistency | p50_ms | p95_ms |
|---------|------|------------|---|-------------|-----------------------|--------|--------|
| temporal_v0 | hybrid | false | 10 | BAAI/bge-m3 | ? | ? | ? |
| temporal_v0 | hybrid | true  | 10 | BAAI/bge-m3 | ? | ? | ? |
```

### Abstention block

```
| dataset | mode | score_threshold | n | embed_model | abstention_rate | p50_ms | p95_ms |
|---------|------|-----------------|---|-------------|------------------|--------|--------|
| abstention_v0 | hybrid | 0.5 | 15 | BAAI/bge-m3 | ? | ? | ? |
```

---

## Comparison with related work

Sources for everything below were re-checked in [VERIFIED.md](VERIFIED.md) §3. Cells marked *verify* are documented as not yet confirmed against primary source.

| Feature | Mem0 | Zep / Graphiti | Letta | `mnemos` |
|---|---|---|---|---|
| Hybrid (dense + sparse) out of the box | Partial — graph memory is optional, BM25 not built-in | Yes — graph + vector | **No** — dense embeddings OR substring `LOWER().contains()`, mutually exclusive; no BM25 or tsvector ([`build_passage_query`](https://github.com/letta-ai/letta/blob/main/letta/services/helpers/agent_manager_helper.py)) | Yes — Qdrant RRF over BM25 + BGE-M3 |
| Entity-based retrieval | Via optional graph memory | Yes — knowledge-graph entities | **No** — passages carry flat `tags` list, no relational entities ([`passage_manager`](https://github.com/letta-ai/letta/blob/main/letta/services/passage_manager.py)) | Yes — Postgres entity tables (no graph DB to defend) |
| Contradiction detection at write | Yes — LLM during `ADD` resolves duplicates/contradictions ([Mem0 paper §3](https://arxiv.org/abs/2504.19413)) | Yes — bitemporal invalidation ([Zep paper](https://arxiv.org/abs/2501.13956)) | **No** — `insert_passage` / `create_*_passage_async` are CRUD only ([`passage_manager`](https://github.com/letta-ai/letta/blob/main/letta/services/passage_manager.py)) | Yes — **LLM-judge + NLI baseline reported side-by-side** |
| Continuous temporal-decay weighting | Not in paper, not in docs | Bitemporal validity intervals (a different concept — invalidation, not weighting) | **No** — timestamps used only for `created_at` range filter and asc/desc ordering | Yes — `exp(-λ_i · Δt)`, three importance tiers, tunable via eval |
| Importance-weighted eviction | Not documented | Not documented (history preserved) | **No** — archival grows unbounded; [`summarizer/`](https://github.com/letta-ai/letta/tree/main/letta/services/summarizer) compresses the LLM context window (different concept) | Yes — composite `I·w_I + R·w_R + log(1+A)·w_A`, tunable weights |
| Public, versioned eval dataset for memory | Reports on LOCOMO (external) | Reports on DMR + LongMemEval (external) | **No** — `tests/data/` is integration-test fixtures (PDFs, source files), no benchmark | Yes — `mnemos-bench-v1` (75 cases, this repo) |
| One-command local reproduction | Not the focus | Not the focus | Not the focus | **Yes — explicit goal**; `docker compose up && make eval-compare` |

Letta cells were re-checked against `main` of `letta-ai/letta` on 2026-05-26; full evidence with file paths and quoted code is in [VERIFIED.md §3](VERIFIED.md#3-competitor-feature-audit--partial). Letta is a stateful **agent runtime** whose answer to "memory" is summarising the context window rather than measuring retrieval quality over a versioned dataset — a legitimate different question.

The honest version of the headline:

> `mnemos` is the only system in this comparison that **ships a versioned eval dataset, a configurable temporal-decay function, and a one-command reproducible local eval pipeline**. It does not aim to beat Mem0 or Zep on LOCOMO. It aims to make memory-system behaviour measurable and tunable by anyone with Docker.

---

## Limitations

Said up front and in the writeup, not buried.

- **Dataset is small** (n=75). Hand-authored by one person means it carries the author's blind spots. The runners support pointing at any JSONL with the right schema, so anyone can extend it.
- **English only** in v1. Multi-language is roadmap, not promised.
- **LLM judge is non-deterministic.** Temperature is the default; structured tool-use reduces variance but does not eliminate it. Each leaderboard row records the model name so runs are at least comparable when the model is held fixed.
- **NLI baseline cannot distinguish `supersedes` from `contradicts`** — symmetric NLI has no notion of which fact came later. The mapping falls back to `CONTRADICTS` and the reason field says so explicitly; the writeup documents this rather than reporting a fake `supersedes` accuracy.
- **Decay applied post-Qdrant** in Python (overfetch 3×, re-rank, truncate). For pools much larger than 10k memories per user the overfetch will start to dominate latency; the cleaner alternative is Qdrant's native `FormulaQuery` for score boosting, deferred to v2.
- **BM25 statistics are not refit** on the mnemos corpus — fastembed's `Qdrant/bm25` uses pre-trained IDF/avgdl from its own background corpus. On heavily domain-shifted datasets, refitting would help and is documented in the docstring as a v2 candidate.
- **Letta comparison cells were filled in by reading the Letta source on `main` (2026-05-26)**, not by quoting their docs. Specific paths are cited in [VERIFIED.md §3](VERIFIED.md#3-competitor-feature-audit--partial). The comparison is restricted to features that exist as code in the upstream repo; any roadmap items they announce later belong in a future revision.
- **First-run cost is real.** BGE-M3 weighs ~700 MB and the service image build is 3–5 minutes on a warm uv cache, ~10 minutes cold.

---

## Quickstart

Requires Docker Desktop, Python 3.12+, [`uv`](https://docs.astral.sh/uv/), and GNU Make.

```powershell
git clone https://github.com/alvarocanoo/mnemos.git
cd mnemos
make sync               # uv sync — installs the workspace and its deps
make up                 # docker compose up: postgres, qdrant, service, dashboard
make verify-stack       # hits /healthz on all three
make eval-compare       # ingests seed_v0, runs dense + hybrid, appends both rows
Get-Content leaderboard.md
```

Then point your browser at `http://localhost:3000` for the dashboard. It mounts `leaderboard.md` read-only and re-reads on every request — keep adding eval rows and refresh.

For contradiction evals (LLM judge), set `ANTHROPIC_API_KEY` in the host shell **before** `make up`; docker-compose passes it through to the service container. The NLI baseline runs entirely locally, no key required.

### Manual API probing

```powershell
curl http://localhost:8000/readyz
curl -X POST http://localhost:8000/memories `
  -H "Content-Type: application/json" `
  -d '{"content":"My favourite colour is teal","user_id":"me"}'
curl -X POST http://localhost:8000/search/hybrid `
  -H "Content-Type: application/json" `
  -d '{"query":"what colour do I like","user_id":"me","limit":5}'
curl -X POST http://localhost:8000/contradiction/detect `
  -H "Content-Type: application/json" `
  -d '{"memory_a":"The Q3 budget is 450k EUR","memory_b":"The Q3 budget is 600k EUR"}'
```

### Per-task eval targets

| Make target | Dataset | What it does |
|---|---|---|
| `make eval` | `seed_v0.jsonl` | Single-hop recall, dense mode |
| `make eval-hybrid` | `seed_v0.jsonl` | Single-hop recall, hybrid mode |
| `make eval-compare` | `seed_v0.jsonl` | Both modes back-to-back |
| `make eval-multi` | `multi_session_v0.jsonl` | Multi-session reasoning, hybrid mode |
| `make eval-contradiction` | `contradiction_v0.jsonl` | LLM judge (needs `ANTHROPIC_API_KEY`) |
| `make eval-nli` | `contradiction_v0.jsonl` | NLI baseline only |
| `make eval-compare-judges` | `contradiction_v0.jsonl` | Both judges, side-by-side gap |
| `make eval-temporal` | `temporal_v0.jsonl` | `temporal_consistency`, decay on |
| `make eval-compare-decay` | `temporal_v0.jsonl` | Decay OFF vs ON, gap reported |
| `make eval-abstention` | `abstention_v0.jsonl` | `abstention_rate` with `--threshold 0.5` |
| `make bench-build` | (regenerates) | Concatenates the 5 files into `mnemos_bench_v1.jsonl` |

---

## Project structure

```
mnemos/
  packages/
    core/        # mnemos library: storage, retrieval, memory ops, embeddings,
                 # decay, eviction, contradiction (judge + NLI baseline)
    service/     # FastAPI HTTP wrapper + Dockerfile + entrypoint (alembic + uvicorn)
    eval/        # mnemos-eval CLI + datasets + runners + metrics + leaderboard
    dashboard/   # Next.js 16 read-only dashboard (server components only)
  docker-compose.yml
  Makefile
  pyproject.toml + uv.lock   # uv workspace
  ARCHITECTURE.md            # module-level paths and decision rationale
  VERIFIED.md                # external-claim verification log (W0 + ongoing)
```

---

## Roadmap

Hard rule: cutoffs cut scope, never extend dates. Where reality forced a scope cut, it is documented here rather than rewritten as if it were always planned that way.

| Milestone | Status | Scope | Notes |
|---|---|---|---|
| **v0.1** | ✅ shipped | Schema, write/read, dense retrieval, eval skeleton with `recall@k`, `make up` end-to-end | 20-case dataset |
| **v0.5** | ✅ shipped | Hybrid BM25+dense+RRF; LLM judge + NLI baseline; temporal decay; importance-weighted eviction; Next.js dashboard | 75-case `mnemos-bench-v1`; 4 leaderboard schemas |
| **v1.0** | 🚧 in progress | First real leaderboard row on author hardware; two blog posts published; Letta comparison cells filled in from source review | Pending: Docker run + writeup execution |
| **v2.0** | future | Dataset to 150–300 cases; native Qdrant `FormulaQuery` for decay; refit BM25 on corpus; multi-language | |

---

## Related work

- **Mem0** — [Building Production-Ready AI Agents with Scalable Long-Term Memory (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413) · [docs.mem0.ai](https://docs.mem0.ai). LLM-driven ADD/UPDATE/DELETE; vector retrieval.
- **Zep / Graphiti** — [A Temporal Knowledge Graph Architecture for Agent Memory (arXiv:2501.13956)](https://arxiv.org/abs/2501.13956). Bitemporal validity intervals on a knowledge graph.
- **Letta** — [github.com/letta-ai/letta](https://github.com/letta-ai/letta). Memory-first agent runtime: archival passages are stored in Postgres with embeddings; retrieval is either dense (cosine) or substring `contains`, mutually exclusive. Context-window management is handled by a separate summarizer subsystem. See [VERIFIED.md §3](VERIFIED.md#3-competitor-feature-audit--partial) for source-level breakdown.
- **LongMemEval** — [Benchmarking Chat Assistants on Long-Term Interactive Memory (arXiv:2410.10813, ICLR 2025)](https://arxiv.org/abs/2410.10813) · [repo](https://github.com/xiaowu0162/longmemeval). The academic benchmark of record; `mnemos-bench` is intentionally smaller, owned, and instrumented for system-level metrics LongMemEval does not measure (latency, decay behaviour, eviction).
- **Anthropic API & tool-use** — [platform.claude.com docs](https://platform.claude.com/docs/en/api/overview).
- **Qdrant hybrid queries** — [docs](https://qdrant.tech/documentation/concepts/hybrid-queries/) (RRF + DBSF fusion).

---

## License

TBD (Apache-2.0 or MIT). To be decided before v1.0 is announced publicly.

---

## Author

Built by [@alvarocanoo](https://github.com/alvarocanoo) as the third project of a 2026 AI-engineer portfolio. Designed and implemented over a deliberate cadence with hard milestone cutoffs and a per-commit verification log. See [ARCHITECTURE.md](ARCHITECTURE.md) for module-level design rationale, [VERIFIED.md](VERIFIED.md) for the external-claim verification trail, and the project's git history for the step-by-step decisions behind each subsystem.
