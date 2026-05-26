# mnemos

> Agent memory system with a public, reproducible evaluation framework.
> Hybrid retrieval, contradiction detection, configurable temporal decay, importance-weighted eviction — all measurable from a single `make eval` command.

**Status**: v0.5 partial — hybrid retrieval (BM25 + dense + RRF), precision@k, and contradiction detection (LLM-judge with Claude Haiku 4.5) landed; NLI baseline, temporal decay, eviction, dashboard pending. See [ARCHITECTURE.md](ARCHITECTURE.md) and [VERIFIED.md](VERIFIED.md).

---

## Why this project exists

Most agent memory systems claim "works well." Few publish a dataset, fewer publish reproducible metrics, almost none ship a one-command local reproduction. `mnemos` exists to make memory-system behavior **measurable and tunable** by anyone with Docker.

This is *not* a benchmark-chasing attempt. The goal is not to beat Mem0 or Zep on LOCOMO. The goal is to ship the **measurement infrastructure** alongside a reference implementation that anyone can compare against, modify, and improve.

---

## What it does (planned for v1.0)

- **Hybrid retrieval**: RRF fusion over dense embeddings + BM25 sparse + entity-filtered SQL.
- **Contradiction detection**: LLM-as-judge primary, NLI baseline reported alongside (so the *gap* is measurable).
- **Temporal decay**: configurable exponential weighting per importance tier — `w(t) = exp(-λ_i · Δt_days)`.
- **Importance-weighted eviction**: composite score `I·w_I + R·w_R + log(1+A)·w_A`, tunable weights as an eval axis.
- **Versioned eval dataset** (`mnemos-bench-v1`): 300 hand-authored examples across 5 task types.
- **Reproducible leaderboard**: `make eval` runs the full suite locally and appends a row with git SHA, model pins, all metrics.

---

## Quick start (v0.1 — what works today)

Requires Docker Desktop, Python 3.12+, `uv`, GNU Make.

```powershell
git clone https://github.com/alvarocanoo/mnemos.git
cd mnemos
make sync               # uv sync (installs workspace + deps)
make up                 # build + start postgres, qdrant, service
make verify-stack       # hits /healthz on all three
make eval-compare       # ingest seed_v0.jsonl, run dense + hybrid, append both rows
Get-Content leaderboard.md
```

First `make up` builds the service image (~3-5 min on first run; subsequent rebuilds use the uv cache layer). First `make eval` downloads BGE-M3 (~2 GB) into a Docker volume; subsequent runs reuse it.

Manual probe of the API:

```powershell
curl http://localhost:8000/readyz
curl -X POST http://localhost:8000/memories `
  -H "Content-Type: application/json" `
  -d '{"content":"My favorite color is teal","user_id":"me"}'
curl -X POST http://localhost:8000/search/dense `
  -H "Content-Type: application/json" `
  -d '{"query":"what color do I like","user_id":"me","limit":5}'
curl -X POST http://localhost:8000/search/hybrid `
  -H "Content-Type: application/json" `
  -d '{"query":"what color do I like","user_id":"me","limit":5}'
curl -X POST http://localhost:8000/contradiction/detect `
  -H "Content-Type: application/json" `
  -d '{"memory_a":"The Q3 budget is 450k EUR","memory_b":"The Q3 budget is 600k EUR"}'
```

For `make eval-contradiction` and the `/contradiction/detect` endpoint, set `ANTHROPIC_API_KEY` in the host shell before `make up` (docker-compose passes it through to the service container).

---

## Project structure

```
mnemos/
  packages/
    core/        # mnemos library: storage (Postgres + Qdrant), retrieval, memory ops, embeddings
    service/     # FastAPI HTTP wrapper + Dockerfile + entrypoint
    eval/        # mnemos-eval CLI: dataset + runner + metrics + leaderboard
    # dashboard/ # v0.5 — Next.js read-only views
  docker-compose.yml
  Makefile
  pyproject.toml + uv.lock   # uv workspace
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for module-level detail and design rationale.

---

## Roadmap with hard cutoffs

Scope cuts before timeline extensions. If a milestone slips, the rule is to ship reduced scope, not to push the date.

| Milestone | Target | Scope | If we slip |
|---|---|---|---|
| **v0.1** | W1–W2 | Dense retrieval, write/read API, eval skeleton, `docker compose up` works | Drop Qdrant, use pgvector |
| **v0.5** | W3–W5 | Hybrid (RRF), entity extraction, contradiction v1 (LLM-judge), decay, dataset @ 150, dashboard read-only | Drop entity retrieval |
| **v1.0** | W6–W8 | Eviction policy, NLI baseline, dataset @ 300, auto leaderboard, 2 blog posts published | Ship without NLI baseline; document limitation |

---

## Comparison with existing systems

A detailed comparison vs. Mem0, Zep/Graphiti, and Letta is **planned for the README at v1.0**, after the [pending verifications](VERIFIED.md#8-pending-actions-before-readme-v10) are done.

Headline differentiator (defendable, no superlatives): *`mnemos` is the only system in scope that ships a versioned eval dataset, a configurable temporal-decay function, and a one-command reproducible local eval pipeline.*

---

## Related work

- **Mem0** — [paper](https://arxiv.org/abs/2504.19413), [docs](https://docs.mem0.ai). Production-oriented memory with LLM-based ADD/UPDATE/DELETE.
- **Zep / Graphiti** — [paper](https://arxiv.org/abs/2501.13956). Temporal knowledge graph with bitemporal validity.
- **LongMemEval** — [paper](https://arxiv.org/abs/2410.10813) (ICLR 2025), [repo](https://github.com/xiaowu0162/longmemeval). Academic benchmark; `mnemos-bench` is smaller, owned, and instrumented for system-level metrics.

---

## License

TBD (likely Apache-2.0 or MIT).

---

## Author

Built by [@alvarocanoo](https://github.com/alvarocanoo) as a portfolio project demonstrating production-grade design + rigorous evaluation. See `ARCHITECTURE.md` for the full design rationale, and `VERIFIED.md` for the W0 verification log behind every external claim.
