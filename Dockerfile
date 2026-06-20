# =============================================================================
# Dockerfile de l'API OncoLake
#
# Utilise uv (gestionnaire de paquets rapide, ecrit en Rust) pour installer
# les dependances depuis pyproject.toml. On installe SANS le groupe [dev] :
# l'image de prod ne doit pas embarquer pytest, ruff, etc.
# =============================================================================

FROM python:3.12-slim

# uv : copie du binaire depuis l'image officielle (pas de pip install d'uv)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# --- Couche dependances (mise en cache tant que pyproject ne change pas) ---
# On copie d'abord SEULEMENT pyproject.toml : si seul le code change ensuite,
# Docker reutilise le cache de cette couche et ne reinstalle pas tout.
COPY pyproject.toml ./
COPY README.md ./

# Installe les deps de base + le groupe ml (l'API peut servir des predictions).
# --system : installe dans l'environnement du conteneur, pas dans un venv.
RUN uv pip install --system --no-cache ".[ml]"

# --- Couche code (change souvent, donc placee en dernier) ---
COPY src/ ./src/

# Le port expose par uvicorn
EXPOSE 8000

# Lancement de l'API.
CMD ["uvicorn", "src.oncolake.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
