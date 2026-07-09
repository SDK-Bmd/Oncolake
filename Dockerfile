# =============================================================================
# Dockerfile de l'API OncoLake
#
# Utilise uv (gestionnaire de paquets rapide, ecrit en Rust) pour installer
# les dependances depuis pyproject.toml. On installe SANS le groupe [dev] :
# l'image de prod ne doit pas embarquer pytest, ruff, etc.
# =============================================================================

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml ./
COPY README.md ./
RUN uv pip install --system --no-cache ".[ml]"
COPY src/ ./src/


EXPOSE 8000

# Lancement de l'API.
CMD ["uvicorn", "src.oncolake.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
