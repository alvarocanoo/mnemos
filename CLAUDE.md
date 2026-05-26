# CLAUDE.md — Project-specific rules for `mnemos`

> Global rules live in `C:\Users\acano\.claude\CLAUDE.md`. This file adds project-specific context.

---

## Project context

- `mnemos` is an agent memory system with a public, reproducible eval framework.
- Status: pre-v0.1 — week 0 verification done. See `VERIFIED.md`.
- Full plan: `C:\Users\acano\.claude\plans\quiero-un-3-proyecto-valiant-tower.md`.
- This is project 3 of the AI Engineer portfolio (see `project_portfolio_2026` memory). Positioned as the primary link in CV/LinkedIn.
- Repo: https://github.com/alvarocanoo/mnemos (private until v0.1, then public).

---

## Language

- Code, comments, commit messages, README, blog post titles → **English**.
- Conversation with the user → **Spanish** (per global CLAUDE.md).
- Blog posts → bilingual (ES + EN); see roadmap in the project plan.

---

## Architectural commitments (do not silently violate)

- **Storage split**: Postgres = source of truth for memory metadata, timestamps, importance, access counts, eval runs. Qdrant = dense + sparse vectors. No graph DB.
- **Embedding model default**: BGE-M3 (BAAI/bge-m3) — confirmed in VERIFIED.md §5. `bge-small-en-v1.5` is the fast-mode fallback only.
- **LLM judge default**: Claude Haiku 4.5 (`claude-haiku-4-5`). Sonnet 4.6 optional; Ollama Llama 3 as local-only fallback. Confirmed pricing in VERIFIED.md §4.
- **Fusion**: RRF default, DBSF alternative. Verified Qdrant-native in VERIFIED.md §2.
- **Deployment target**: 100% local Docker. No cloud assumption.

---

## Milestone discipline

| Milestone | Hard cutoff | Cut rule if slipping |
|---|---|---|
| v0.1 | End of W2 | Drop Qdrant, use pgvector |
| v0.5 | End of W5 | Drop entity-based retrieval |
| v1.0 | End of W8 | Drop NLI baseline, document limitation |

**Non-negotiable**: cutoffs cut scope, never extend dates. If the user asks to extend a milestone, push back and propose the scope cut instead.

---

## Eval framework is the product

Every feature shipped must have a metric in `packages/eval/`. No code merges to main without:
1. A test (unit or integration).
2. An eval metric or contribution to one.
3. A leaderboard entry showing before/after numbers if the change touches retrieval, contradiction, or decay.

---

## Coding conventions

- Python: 3.12+, type hints required on public APIs, ruff + mypy in CI.
- Comments: **default to none**. Only add when *why* is non-obvious (per global CLAUDE.md rule).
- Tests: pytest, real Postgres + Qdrant via testcontainers (no mocks for storage layer).
- Migrations: alembic, never edit existing migrations.
- Next.js: 14+, App Router, TS strict, no client-side state libraries until justified.

---

## When in doubt

1. Re-read this file and the plan at `C:\Users\acano\.claude\plans\quiero-un-3-proyecto-valiant-tower.md`.
2. Check `VERIFIED.md` for any claim about external systems.
3. If a decision touches architecture (storage, models, fusion), ask before changing.
