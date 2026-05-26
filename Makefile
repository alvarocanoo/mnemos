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
	@echo "  make eval            run mnemos-eval on seed_v0.jsonl, append leaderboard row"
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
		--runs-dir eval-runs

test:
	uv run pytest

lint:
	uv run ruff check

demo:
	@echo "TODO v0.5: open dashboard at http://localhost:3000"
	@exit 1

bench-hardware:
	@echo "TODO v1.0: record CPU/RAM and benchmark retrieval latency"
	@exit 1
