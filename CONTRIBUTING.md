# Contributing to mnemos

Thanks for the interest. This project is a portfolio reference implementation, not an attempt at a production library competing with Mem0 / Zep / Letta — so the bar for contributions is "does this make the dataset, the eval, or the writeup more defendable?" rather than "does this add a feature".

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) (the project uses a uv workspace)
- Node 22+ (only if you touch `packages/dashboard`)
- Docker Desktop (only if you want to run end-to-end against postgres + qdrant)

## Setup

```powershell
git clone https://github.com/alvarocanoo/mnemos.git
cd mnemos
uv sync
uv run pytest -q   # 71 tests, ~10s; no Docker required
```

## Before opening a PR

Run all three locally:

```powershell
uv run ruff check
uv run ruff format --check
uv run pytest -q
```

CI runs the same three plus a `packages/dashboard` Next.js build. A red CI block fails the PR.

## Where to put a change

- **Retrieval / contradiction / decay / eviction code** → `packages/core/mnemos/`
- **HTTP routes** → `packages/service/app/routers/`
- **Eval metrics, runners, datasets** → `packages/eval/mnemos_eval/`
- **Dashboard pages** → `packages/dashboard/app/`

## Datasets

If you add or change a case in `packages/eval/mnemos_eval/datasets/*.jsonl`:

- The case must follow the per-task `gold` shape in [schema.md](packages/eval/mnemos_eval/datasets/schema.md).
- After editing per-type files, regenerate the combined bench: `make bench-build`.
- Hand-authored is preferred over LLM-generated to keep the dataset auditable. If you use an LLM to seed candidates, review every line before commit.

## External claims

If a PR or a doc claim references an upstream library (Mem0, Zep, Letta, Qdrant, Anthropic), check the claim against the upstream source and add the evidence to [VERIFIED.md](VERIFIED.md). Unverified comparisons are a regression even if the code is clean.

## License

By contributing, you agree your work is licensed under the project's [Apache License 2.0](LICENSE).
