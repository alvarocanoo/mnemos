# ARCHITECTURE.md

> Module-level design and rationale for `mnemos`. Full project plan including milestones, red-team, and writeup roadmap lives at `~/.claude/plans/quiero-un-3-proyecto-valiant-tower.md`.

---

## Storage split

| Data | Store | Rationale |
|---|---|---|
| Memory text + metadata + timestamps + importance + access counts | Postgres | Transactional updates (decay job, eviction, access bumps); SQL filters; auditable |
| Dense embedding | Qdrant | Native ANN, payload filters, hybrid fusion |
| Sparse vector (BM25-style) | Qdrant sparse vectors | Verified native (see VERIFIED.md §2) |
| Entities + memory↔entity edges | Postgres relational | SQL joins, no graph DB to defend in interview |
| Eval runs, scores, leaderboard rows | Postgres | Queryable history |

---

## Module layout (target)

```
packages/
  core/
    mnemos/
      storage/
        postgres.py       # SQLAlchemy + alembic migrations
        qdrant.py         # collection mgmt, dense+sparse vectors
        schema.sql        # source of truth for the split
      retrieval/
        dense.py          # Qdrant dense search
        sparse.py         # BM25 via Qdrant sparse
        entity.py         # entity-filtered SQL query
        fusion.py         # RRF default, DBSF alternative
        ranker.py         # fusion_score * decay * importance
      memory/
        ops.py            # write / read / update / delete / list
        decay.py          # w = exp(-lambda_i * delta_days), 3 tiers
        eviction.py       # composite score, evict bottom-N
        contradiction.py  # detect_conflict() -> verdicts
      extraction/
        facts.py          # LLM extraction (Haiku 4.5 default, Llama local opt)
        entities.py       # spaCy en_core_web_sm + LLM fallback
    tests/
  service/                # FastAPI wrapper
    app/
      routers/{memories,search,eval,admin}.py
      deps.py
      main.py
  eval/                   # the differentiator
    mnemos_eval/
      datasets/
        mnemos_bench_v1.jsonl
        schema.md
      runners/
        run_suite.py      # CLI: `mnemos-eval run --config X`
        fixtures.py       # seeded RNG, deterministic ordering
      metrics/
        recall.py         # recall@k (k=1,5,10)
        precision.py
        contradiction_f1.py
        temporal.py       # temporal_consistency_score
        latency.py        # p50/p95/p99
      report/
        leaderboard.py    # generates leaderboard.md + JSON
  dashboard/              # Next.js, read-only
    app/
      memories/page.tsx
      graph/page.tsx
      eval/page.tsx
      timeline/page.tsx
```

---

## Key technical decisions (alternatives with criterion)

| Decision | Chosen | Alternative | Criterion |
|---|---|---|---|
| Fusion | RRF (k=60) | DBSF | RRF is parameter-light and Qdrant-native; DBSF needs measured score distributions — defer |
| Sparse retrieval | BM25 via Qdrant sparse | SPLADE via fastembed | BM25 is defendable and tunable; SPLADE adds ML opacity in interview |
| Contradiction | LLM-as-judge primary + NLI (deberta-v3-mnli) baseline | Cosine threshold only | Cosine confuses paraphrase with contradiction; reporting LLM vs NLI gap is the contribution |
| Temporal decay | Per-importance-tier exponential `w(t) = exp(-λ_i · Δt_days)` (3 tiers) | Sigmoid; Ebbinghaus power-law | Exponential = one parameter per tier, defendable, tunable via eval |
| Eviction | Composite `I·w_I + R·w_R + log(1+A)·w_A`, evict bottom-N | LRU; FIFO | Defendable as "importance + usage weighted"; weights become an eval axis |
| Entity extraction | spaCy `en_core_web_sm` + LLM fallback | LLM-only | spaCy = reproducible, fast, zero API cost; LLM only when spaCy misses |
| Embedding model | BGE-M3 (default) + bge-small-en-v1.5 (fast mode) | OpenAI text-embedding-3-small | Local-only → `docker compose up` works without an API key (see VERIFIED.md §5) |
| LLM judge | Claude Haiku 4.5 (default) + Sonnet 4.6 (option) + Llama 3 local (fallback) | OpenAI gpt-4o-mini | Pricing verified (VERIFIED.md §4); local Ollama option allows reproduction without billing |

---

## Eval framework — `mnemos-bench-v1`

### Dataset

- **Size at v1.0**: 300 examples (50 seed → 150 → 300). Hand-authored + LLM-augmented with manual review.
- **5 task types** (60 each):
  1. Single-hop recall — fact stated once, ask N turns later.
  2. Multi-session reasoning — combine facts across 2+ sessions.
  3. Temporal update — fact stated then contradicted; must retrieve the current truth.
  4. Contradiction labeling — pairs `(mem_a, mem_b)` with gold label `{contradicts, supersedes, independent, paraphrase}`.
  5. Abstention — query for info never stored; must return empty, not hallucinate.

- **Format** (`mnemos_bench_v1.jsonl`):
  ```
  {"id":"...", "task_type":"temporal_update", "history":[...],
   "query":"...", "gold":{"memory_ids":["m12"], "answer":"...",
   "contradiction_labels":[{...}], "should_abstain":false},
   "seed":42, "version":"v1"}
  ```

- Anchor results also on **LongMemEvalS** (the small split of LongMemEval, see VERIFIED.md §1) for external comparability.

### Metrics with v1.0 targets

| Metric | Definition | Target v1.0 |
|---|---|---|
| `recall@k` | `\|gold_ids ∩ top_k_ids\| / \|gold_ids\|` averaged across queries | recall@10 ≥ 0.80 |
| `precision@k` | `\|gold_ids ∩ top_k_ids\| / k` | precision@5 ≥ 0.40 |
| `contradiction_f1` | F1 vs gold `{contradicts, supersedes}` collapsed positive | ≥ 0.70 (LLM-judge); NLI baseline reported separately |
| `temporal_consistency` | In `temporal_update` items, fraction where the current-truth memory ranks above the superseded one in top-5 | ≥ 0.75 |
| `abstention_rate` | TN / (TN+FP) on abstention tasks | ≥ 0.85 |
| `latency_p50` / `p95` | Retrieval latency on warm Qdrant, ~10k memories | p50 < 80 ms, p95 < 250 ms (local Docker, single node) |

If any v1.0 target misses by >15%, README documents the gap + hypothesis + next-step. No inflation.

### Reproducibility

- Seeded RNG in `fixtures.py`; deterministic Qdrant collection naming per run.
- Dataset versioned in repo with SHA in each leaderboard entry.
- Embedding model + LLM judge pinned in `eval.config.yaml`; config mismatch refuses to write a leaderboard row.
- **One command**: `make eval` → docker compose up + ingest + suite + writes `leaderboard.md` + `eval_run_<git_sha>.json`.

### Leaderboard columns

`version | git_sha | embed_model | judge_model | recall@10 | precision@5 | contradiction_f1 | temporal_consistency | p95_ms | timestamp`

Baselines pinned: `naive_dense_only`, `bm25_only`, `mnemos_hybrid_no_decay`, `mnemos_full`.

---

## Acceptance checklist (gate to declare v1.0)

- [ ] Fresh clone on Windows 11 + Docker Desktop → `make eval` green in <15 min
- [ ] Leaderboard shows all 4 baselines + `mnemos_full`
- [ ] All v1.0 numeric targets met OR gap documented per Section above
- [ ] 2 blog posts published, 2 drafted
- [ ] README paper-light complete with diagram
- [ ] LongMemEvalS results table populated
- [ ] `VERIFIED.md` pending actions resolved (see §8)
