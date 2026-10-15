# F1 Stats

Serveur léger qui récupère les données F1 (calendrier, horaires, classements, résultats) via l'API [jolpica](https://api.jolpi.ca/ergast/f1/) et les expose en JSON minimal — conçu pour qu'un ESP32 puisse les consommer en une seule requête.

## Stack

- **Python 3.13+** / **FastAPI**
- **httpx** (appels async vers l'API F1)
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

## API

### Endpoints

| Endpoint | Description | Clé JSON |
|---|---|---|
| `GET /api/v1/calendar?year=2026` | Calendrier complet (circuits, sessions) | `cal` |
| `GET /api/v1/next` | Prochain weekend de course | `next` |
| `GET /api/v1/standings/drivers` | Classement pilotes | `drv` |
| `GET /api/v1/standings/constructors` | Classement constructeurs | `con` |
| `GET /api/v1/results/race?round=N` | Résultats de la course | `res` |
| `GET /api/v1/results/qualifying?round=N` | Résultats qualifs | `qual` |
| `GET /api/v1/results/sprint?round=N` | Résultats sprint | `spr` |
| `GET /api/v1/health` | Santé du serveur | `ok`, `ts` |

Tous les endpoints optionnels : `?year=YYYY` (défaut = année en cours).

### Sessions disponibles par weekend

Format normal → `fp1`, `fp2`, `fp3`, `qual`, `race`
Format sprint → `fp1`, `qual`, `sprint`, `sq`, `race`

### Exemple de réponse

```
GET /api/v1/standings/drivers

{
  "drv": [
    {"pos": 1, "name": "Andrea Kimi Antonelli",
     "team": "Mercedes", "pts": 340},
    ...
  ]
}
```

Les clés sont courtes (`drv`, `con`, `rnd`, `pos`, `pts`) pour minimiser le parsing sur ESP32.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## CI / Docker Hub

À chaque push sur `main`, GitHub Actions :

1. Lance les tests
2. Build l'image Docker
3. Push sur Docker Hub (`:latest`, `:<sha>`)

Pour un tag git (`v1.0`), l'image est aussi taguée `:v1.0`.

**Secrets GitHub requis :**

- `DOCKER_USERNAME` — ton username Docker Hub
- `DOCKER_TOKEN` — token d'accès personnel Docker Hub

## Structure

```
.
├── Dockerfile
├── docker-compose.yml
├── server/
│   ├── main.py          # Routes FastAPI
│   ├── f1_client.py     # Appels API F1 + parsing
│   └── cache.py         # Cache TTL 10 min
├── tests/
│   └── test_api.py
└── .github/workflows/ci.yml
```