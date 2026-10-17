# F1 Stats

Serveur léger qui récupère les données F1 (calendrier, prochain GP, classement pilotes) via l'API [jolpica](https://api.jolpi.ca/ergast/f1/) et les expose en JSON minimal — conçu pour qu'un ESP32 puisse les consommer en une seule requête.

## Stack

- **Python 3.13+** / **FastAPI**
- **httpx** (client async partagé vers l'API F1)
- Cache mémoire TTL (1h le weekend, 24h sinon) + rate limiting 30 req/min/IP
- **Docker** / **Docker Compose**

## Démarrage rapide

```bash
# Avec Docker (recommandé)
docker compose up -d

# Ou en local
source .venv/bin/activate
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Le serveur écoute sur `http://localhost:8000`.

### Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `F1_ENABLE_DOCS` | *(off)* | `1`/`true` pour activer Swagger (`/docs`) et OpenAPI (`/openapi.json`) |
| `F1_DOCKER_USERNAME` | *(requis par compose)* | Username Docker Hub pour le nom de l'image |

> **Avertissement :** service HTTP uniquement, prévu pour un usage LAN / ESP32 derrière un reverse proxy.

## API

### Endpoints

| Endpoint | Description | Clé JSON |
|---|---|---|
| `GET /api/v1/calendar?year=2026` | Calendrier complet de la saison | `cal` |
| `GET /api/v1/next` | Prochain Grand Prix | `next` |
| `GET /api/v1/standings` | Classement pilotes | `drv` |
| `GET /api/v1/health` | Santé du serveur | `ok`, `ts` |

Paramètres optionnels : `?year=YYYY` (défaut = année en cours), `?round=N` (standings uniquement).

> **Notes `/next`** :
> - Un GP qui a lieu aujourd'hui reste « next » jusqu'à minuit UTC (comparaison sur la date seule).
> - **Hors saison** (plus aucun GP futur et pas d'année explicite) : bascule automatique sur le 1er GP de la saison N+1 ; fallback sur le dernier GP si N+1 est indisponible.

### Exemple de réponse

```
GET /api/v1/standings

{
  "drv": [
    {"pos": 1, "name": "A. Antonelli", "pts": 340},
    {"pos": 2, "name": "M. Verstappen", "pts": 300},
    ...
  ]
}
```

Les clés sont courtes (`drv`, `rnd`, `pos`, `pts`) pour minimiser le parsing sur ESP32.

### Codes d'erreur

| Code | Signification |
|---|---|
| 422 | Paramètre invalide (`year`, `round`) |
| 429 | Rate limit dépassé (30 req/min/IP) |
| 503 | API F1 amont indisponible |

Documentation complète : [API.md](API.md) · Swagger interactif : `/docs` *(désactivé par défaut, voir `F1_ENABLE_DOCS`)*

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Les tests sont **100 % offline** : l'API jolpica est mockée avec [respx](https://lundberg.github.io/respx/).

## CI / Docker Hub

GitHub Actions, à chaque push sur `main`, `develop/*`, `refactor/*`, `hotfix/*` et sur les tags :

1. **Lint** (`ruff`) + **audit de sécurité des dépendances** (`pip-audit`) + tests
2. Build l'image Docker
3. **Scan Trivy** — bloque si vulnérabilité CRITICAL/HIGH
4. Push sur Docker Hub (`:latest` sur `main`, `:<tag>` pour les tags git, `:<sha>` sur `develop/*`, `hotfix/*` et `refactor/*`)
5. Création automatique d'une **release GitHub** sur les tags (`latest` pour les tags finaux, **pré-release** pour les `-RC*`)

**Secrets GitHub requis :**

- `DOCKER_USERNAME` — ton username Docker Hub
- `DOCKER_TOKEN` — token d'accès personnel Docker Hub

## Déploiement (production)

Le conteneur est conçu pour tourner **derrière un reverse proxy de confiance** (Traefik, WAF type SafeLine) :

- Uvicorn est lancé avec `--proxy-headers` et le rate limiter lit `X-Forwarded-For` → l'IP réelle du client est respectée. Par défaut uvicorn ne fait confiance qu'à `127.0.0.1` ; si le proxy est sur une autre machine, ajuster avec `--forwarded-allow-ips`.
- ⚠️ Ne pas exposer le conteneur directement sur internet sans proxy : n'importe qui pourrait alors forger `X-Forwarded-For` et contourner le rate limiting.
- Utilisateur non-root (UID 10001), healthcheck intégré, limites mémoire/CPU dans le compose.
- L'API amont est appelée avec **retry automatique** (3 tentatives, backoff 1s/2s) sur 429, 5xx et erreurs réseau.

## Structure

```
.
├── Dockerfile
├── docker-compose.yml
├── server/
│   ├── main.py          # Routes FastAPI + logging + lifespan
│   ├── f1_client.py     # Client httpx partagé, cache, parsing API F1
│   ├── cache.py         # Cache TTL borné (maxsize)
│   └── rate_limit.py    # Rate limiter par IP (X-Forwarded-For)
├── tests/
│   ├── conftest.py      # Payloads mockés de l'API jolpica
│   ├── test_api.py      # Endpoints (offline)
│   ├── test_cache.py
│   └── test_rate_limit.py
└── .github/workflows/ci.yml
```
