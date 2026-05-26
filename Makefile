# mnemos Makefile — v0.1 targets.

.PHONY: up down logs verify-stack seed eval demo bench-hardware sync test lint help

help:
	@echo "mnemos — v0.1 targets"
	@echo "  make sync            uv sync (install workspace deps)"
	@echo "  make up              docker compose up -d (postgres + qdrant + service)"
	@echo "  make down            docker compose down"
	@echo "  make logs            tail service logs"
	@echo "  make verify-stack    check postgres + qdrant + service reachable"
	@echo "  make seed            (alias for make eval — ingest happens inside the suite)"
	@echo "  make eval            run mnemos-eval (dense mode), append leaderboard row"
	@echo "  make eval-hybrid     run mnemos-eval (hybrid BM25+dense RRF) row"
	@echo "  make eval-compare    run BOTH modes back-to-back for side-by-side leaderboard"
	@echo "  make eval-contradiction  run LLM-judge on contradiction_v0.jsonl (needs ANTHROPIC_API_KEY)"
	@echo "  make eval-nli            run NLI baseline (DeBERTa) on contradiction_v0.jsonl (no API key needed)"
	@echo "  make eval-compare-judges run LLM-judge AND NLI baseline back-to-back for the gap"
	@echo "  make eval-temporal       run temporal_consistency on temporal_v0.jsonl (decay ON)"
	@echo "  make eval-compare-decay  run temporal suite with decay OFF and ON for the gap"
	@echo "  make demo            open the dashboard at http://localhost:3000"
	@echo "  make dashboard-logs  tail dashboard logs"
	@echo "  make test            run pytest"
	@echo "  make lint            run ruff check"
	@echo "  make demo            (v0.5) open dashboard at http://localhost:3000"
	@echo "  make bench-hardware  (v1.0) record CPU/RAM + run latency benchmark"

sync:
	uv sync

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f service

verify-stack:
	@echo "Checking Postgres..."
	docker exec mnemos-postgres pg_isready -U mnemos -d mnemos
	@echo "Checking Qdrant..."
	curl -fsS http://localhost:6333/healthz && echo " OK"
	@echo "Checking service..."
	curl -fsS http://localhost:8000/healthz && echo ""
	curl -fsS http://localhost:8000/readyz | python -m json.tool

seed: eval

eval:
	uv run mnemos-eval run \
		--dataset packages/eval/mnemos_eval/datasets/seed_v0.jsonl \
		--service-url http://localhost:8000 \
		--leaderboard leaderboard.md \
		--runs-dir eval-runs \
		--mode dense

eval-hybrid:
	uv run mnemos-eval run \
		--dataset packages/eval/mnemos_eval/datasets/seed_v0.jsonl \
		--service-url http://localhost:8000 \
		--leaderboard leaderboard.md \
		--runs-dir eval-runs \
		--mode hybrid

eval-compare:
	uv run mnemos-eval compare \
		--dataset packages/eval/mnemos_eval/datasets/seed_v0.jsonl \
		--service-url http://localhost:8000 \
		--leaderboard leaderboard.md \
		--runs-dir eval-runs

eval-contradiction:
	uv run mnemos-eval contradiction \
		--dataset packages/eval/mnemos_eval/datasets/contradiction_v0.jsonl \
		--service-url http://localhost:8000 \
		--leaderboard leaderboard.md \
		--runs-dir eval-runs \
		--judge llm

eval-nli:
	uv run mnemos-eval contradiction \
		--dataset packages/eval/mnemos_eval/datasets/contradiction_v0.jsonl \
		--service-url http://localhost:8000 \
		--leaderboard leaderboard.md \
		--runs-dir eval-runs \
		--judge nli

eval-compare-judges:
	uv run mnemos-eval compare-judges \
		--dataset packages/eval/mnemos_eval/datasets/contradiction_v0.jsonl \
		--service-url http://localhost:8000 \
		--leaderboard leaderboard.md \
		--runs-dir eval-runs

eval-temporal:
	uv run mnemos-eval temporal \
		--dataset packages/eval/mnemos_eval/datasets/temporal_v0.jsonl \
		--service-url http://localhost:8000 \
		--leaderboard leaderboard.md \
		--runs-dir eval-runs \
		--mode hybrid \
		--apply-decay

eval-compare-decay:
	uv run mnemos-eval compare-decay \
		--dataset packages/eval/mnemos_eval/datasets/temporal_v0.jsonl \
		--service-url http://localhost:8000 \
		--leaderboard leaderboard.md \
		--runs-dir eval-runs \
		--mode hybrid

test:
	uv run pytest

lint:
	uv run ruff check

demo:
	@echo "Dashboard at http://localhost:3000 (assumes 'make up' has been run)"

dashboard-logs:
	docker compose logs -f dashboard

bench-hardware:
	@echo "TODO v1.0: record CPU/RAM and benchmark retrieval latency"
	@exit 1
