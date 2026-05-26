# VERIFIED.md

> Output of week 0 verification (CLAUDE.md rule 1.1 — zero hallucination).
> Every architectural claim that depends on external state has been re-checked with a primary source in this week. Re-verify before publishing the README v1.0.

**Verification date**: 2026-05-26

---

## 1. arXiv references — ALL VERIFIED

| Paper | arXiv ID | Title | Authors | Submitted | Source |
|---|---|---|---|---|---|
| Mem0 | 2504.19413 | *Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory* | Chhikara, Khant, Aryan, Singh, Yadav | 2025-04-28 | https://arxiv.org/abs/2504.19413 |
| Zep | 2501.13956 | *Zep: A Temporal Knowledge Graph Architecture for Agent Memory* | Rasmussen, Paliychuk, Beauvais, Ryan, Chalef | 2025-01-20 | https://arxiv.org/abs/2501.13956 |
| LongMemEval | 2410.10813 | *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory* | Wu, Wang, Yu, Zhang, Chang, Yu | 2024-10-14 (v1), 2025-03-04 (v2) | https://arxiv.org/abs/2410.10813 — ICLR 2025 |

**Action**: cite as-is in README and blog posts.

---

## 2. Qdrant — hybrid + BM25 sparse — CONFIRMED

Source: https://qdrant.tech/documentation/concepts/hybrid-queries/ (fetched 2026-05-26).

- Sparse vectors supported natively, including BM25-style indices/values pairs.
- Two fusion methods built in:
  - **RRF** (default, recommended). Formula `score = Σ 1/(k + rank)`. Parameter `k` configurable (default 2). Per-prefetch weighting available from v1.17.0+.
  - **DBSF** — Distribution-Based Score Fusion (3-sigma normalization).
- Hybrid in a single query via `prefetch=[sparse_prefetch, dense_prefetch]` + `query=models.RrfQuery(...)` — code sample on the docs page.

**Decision**: keep the original plan. RRF as default fusion; DBSF as alternative measured later. No need for plan B (pgvector + tsvector).

---

## 3. Competitor feature audit — partial

### Mem0 — verified against paper + docs

Sources: https://arxiv.org/abs/2504.19413 + https://docs.mem0.ai/core-concepts/memory-operations + https://docs.mem0.ai/core-concepts/memory-types.

| Feature | Verdict | Evidence |
|---|---|---|
| Contradiction detection | YES | Paper: *"An LLM-based update resolver determines if certain relationships should be obsolete, marking them as invalid"* + *"DELETE for removal of memories contradicted by new information"*. Docs: *"Existing memories are checked for duplicates or contradictions so the latest truth wins"* — only with `infer=True` |
| Temporal decay (continuous weighting) | NO | Paper does not describe; explicitly contrasts with MemoryBank which *"naturally decay over time if unused"*. Docs do not mention. |
| Importance-weighted eviction | NO | Not described in paper or docs. Lifecycle is ADD/UPDATE/DELETE driven by LLM, no importance threshold. |
| Hybrid retrieval (sparse + dense) | NO (dense only) | Paper: *"the system retrieves the top s similar memories using vector embeddings"*. Mem0g adds semantic triplet + entity-centric but still embedding-based. |
| Public eval dataset they own | NO | Reports results on LOCOMO (not theirs). |

### Zep — accepted from paper (arXiv:2501.13956)

Knowledge-graph + bitemporal model. Bitemporal validity intervals (not the same concept as continuous decay weighting — Zep *invalidates* edges; `mnemos` *down-weights* memories). Reports on DMR + LongMemEval but does not ship a turnkey eval CLI.

### Letta — VERIFIED via GitHub source (2026-05-26)

Letta's public docs (`docs.letta.com/`, `docs.letta.com/overview`) only surface marketing copy. The actual retrieval / contradiction / decay / eviction behaviour was read directly from the source on `main` branch of [github.com/letta-ai/letta](https://github.com/letta-ai/letta).

| Feature | Verdict | Source |
|---|---|---|
| Hybrid (sparse+dense) retrieval | **NO** — dense OR substring `contains`, mutually exclusive | [`letta/services/helpers/agent_manager_helper.py`](https://github.com/letta-ai/letta/blob/main/letta/services/helpers/agent_manager_helper.py) `build_passage_query` / `build_agent_passage_query` — if `embedded_text` is set, orders by `cosine_distance(...)`; if not, filters with `func.lower(text).contains(func.lower(query_text))`. No tsvector, no BM25, no RRF |
| Entity-based retrieval | **NO** | Passages carry a `tags` list (deduplicated with `list(set(tags))` in `passage_manager.py`) but tags are flat strings, not relational entities, and the retrieval queries don't join on them |
| Contradiction detection at write | **NO** | [`letta/services/passage_manager.py`](https://github.com/letta-ai/letta/blob/main/letta/services/passage_manager.py) `insert_passage` / `create_*_passage_async` are CRUD only. No duplicate/contradiction check, just tag dedup |
| Continuous temporal-decay weighting | **NO** | Same `build_passage_query`: timestamps used only for `created_at >= start_date` filtering and `created_at.asc()/desc()` ordering. No exponential or sigmoid weight, no half-life concept |
| Importance-weighted eviction over archival | **NO** | Archival passages grow without bound. Letta's [`letta/services/summarizer/`](https://github.com/letta-ai/letta/tree/main/letta/services/summarizer) (`sliding_window`, `self_summarizer`, `summarizer_all`, `compact`) compresses the LLM **context window** — a different concept from evicting stored memories |
| Public versioned eval dataset for memory | **NO** | [`tests/data/`](https://github.com/letta-ai/letta/tree/main/tests/data) contains integration-test fixtures (PDFs, source files, images) — no benchmark dataset for memory retrieval. No `benchmark*` files found via GitHub code search |

**Net comparison vs `mnemos`**: Letta is a stateful agent runtime where "memory" is primarily addressed by *compacting the context window* rather than by *measuring retrieval quality over a versioned dataset*. Both are valid; they answer different questions. `mnemos` is built for the second question.

---

## 4. Pricing — Claude API verified

Source: https://platform.claude.com/docs/en/about-claude/pricing (fetched 2026-05-26).

| Model | Input $/MTok | Output $/MTok | Cache hit $/MTok |
|---|---|---|---|
| Claude Haiku 4.5 | $1 | $5 | $0.10 |
| Claude Sonnet 4.6 | $3 | $15 | $0.30 |
| Claude Opus 4.7 | $5 | $25 | $0.50 |

Batch API: 50% off both input and output.

**Decision for LLM-judge in eval**:
- **Default**: Claude Haiku 4.5. For 300 eval examples × ~2k input + ~500 output: `300 × (2000·$1 + 500·$5) / 1M = $1.35` per full eval run. Trivial.
- **Optional**: Sonnet 4.6 for higher-stakes ablations. Same shape: ~$4.05 per run.
- **Local fallback**: Ollama + Llama 3 (no API key needed) — for reclaimer reproduction without billing.

---

## 5. Embedding model — DECISION CHANGED

Source: https://huggingface.co/BAAI/bge-small-en-v1.5 (fetched 2026-05-26).

`bge-small-en-v1.5` last updated **2023-12**. No 2025-2026 updates. The model card itself recommends BGE-M3 for new projects.

**BGE-M3** characteristics:
- Multilingual (100+ languages).
- Up to **8192 tokens** sequence length (vs. 512 in bge-small).
- Multi-functionality: dense + sparse + ColBERT in one model.
- State of the art on MIRACL and MKQA.
- Trade-off: ~568M params vs 33M — heavier, slower on CPU.

**Decision**:
- **Default for v1.0**: BGE-M3. Aligns with Qdrant hybrid (its sparse vectors can feed Qdrant's sparse index directly), supports longer memories, actively maintained.
- **Fast/CI mode option**: keep bge-small-en-v1.5 as a config switch for smoke tests where speed > quality.
- Both will be **leaderboard axes** (`embed_model` column already in the schema).

---

## 6. spaCy `en_core_web_sm` — DEFERRED

Not blocking for v0.1 (entity extraction is v0.5 scope). Action: smoke-test against 20 examples of the seed dataset before committing to spaCy in v0.5. If recall on entity extraction <70%, swap to LLM extraction primary with spaCy fallback.

---

## 7. Summary — decisions for v0.1

| Original plan | Status after W0 | Final decision |
|---|---|---|
| Qdrant + BM25 sparse + RRF | Confirmed | Keep |
| Pgvector + tsvector plan B | Not needed | Drop |
| bge-small-en-v1.5 embedding | Outdated | **Swap to BGE-M3 default, bge-small fallback for fast mode** |
| Claude Sonnet 4.6 or gpt-4o-mini judge | Pricing OK | **Haiku 4.5 default; Sonnet 4.6 optional; Ollama Llama 3 local fallback** |
| Letta in comparison table | Verified via GitHub source (2026-05-26) | All cells populated from `build_passage_query` + `passage_manager` + `tests/data` evidence (see §3) |
| Mem0 contradiction = YES | Confirmed (paper + docs) | Keep |
| Mem0 decay = NO documentado | Confirmed | Tighten language: "not in paper, not in docs" |

---

## 8. Pending actions before README v1.0

- [x] Read Letta source at `github.com/letta-ai/letta` and fill in the comparison table. **Done 2026-05-26** — see §3 above; paths cited.
- [ ] Smoke-test spaCy `en_core_web_sm` against 20 seed examples (before v0.5).
- [ ] Re-verify Qdrant `RrfQuery` API signature against the installed Qdrant client version when pinning dependencies.
- [ ] Confirm BGE-M3 inference latency on local Docker; if p95 > target, evaluate quantized variant.
