.PHONY: up down install repro api

up:        ## demarre MinIO + cree les buckets
	docker compose up -d

down:      ## arrete MinIO
	docker compose down

install:   ## installe les deps avec uv
	uv venv && uv pip install -e ".[dev]"

repro:     ## execute le pipeline DVC complet
	dvc repro

api:       ## lance la gateway FastAPI
	uvicorn oncolake.api.main:app --reload
