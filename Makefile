# mnemos Makefile — stubs for week 0. Real targets land in v0.1.

.PHONY: up down seed eval demo bench-hardware verify-stack help

help:
	@echo "mnemos — available targets (week 0 stubs)"
	@echo "  make up              docker compose up -d (postgres + qdrant)"
	@echo "  make down            docker compose down"
	@echo "  make verify-stack    check postgres + qdrant are reachable"
	@echo "  make seed            (v0.1) load mnemos-bench-v1 + ingest"
	@echo "  make eval            (v0.1) run full eval suite, append leaderboard row"
	@echo "  make demo            (v0.5) open dashboard"
	@echo "  make bench-hardware  (v1.0) record CPU/RAM + run latency benchmark"

up:
	docker compose up -d

down:
	docker compose down

verify-stack:
	@echo "Checking Postgres..."
	docker exec mnemos-postgres pg_isready -U mnemos -d mnemos
	@echo "Checking Qdrant..."
	curl -fsS http://localhost:6333/healthz && echo " OK"

seed:
	@echo "TODO v0.1: load mnemos-bench-v1 dataset and ingest into stack"
	@exit 1

eval:
	@echo "TODO v0.1: run eval suite, append leaderboard.md row"
	@exit 1

demo:
	@echo "TODO v0.5: open dashboard at http://localhost:3000"
	@exit 1

bench-hardware:
	@echo "TODO v1.0: record CPU/RAM and benchmark retrieval latency"
	@exit 1
