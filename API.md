# API F1 Stats — Documentation

Base URL : `http://<serveur>:8000`

Toutes les réponses sont en JSON. Les clés sont courtes pour minimiser la taille à parser par l'ESP32.

**Rate limit :** 30 requêtes / minute / IP (hors `/api/v1/health`).

**Docs interactives (`/docs`) désactivées par défaut** — définir la variable d'environnement `F1_ENABLE_DOCS=1` pour les activer.

---

## Santé

```
GET /api/v1/health
```

**Réponse :**

```json
{
  "ok": true,
  "ts": "2026-10-15T09:13:17.650560+00:00"
}
```

| Champ | Type | Description |
|---|---|---|
| `ok` | bool | Toujours `true` |
| `ts` | string | Timestamp ISO 8601 (UTC) |

---

## Calendrier

```
GET /api/v1/calendar?year=2026
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int (1950–2100) | année courante | Saison souhaitée |

**Réponse :**

```json
{
  "cal": [
    {
      "rnd": 1,
      "name": "Australian Grand Prix",
      "date": "2026-03-08"
    }
  ]
}
```

| Champ | Type | Description |
|---|---|---|
| `rnd` | int | Numéro du round |
| `name` | string | Nom du Grand Prix |
| `date` | string | Date de la course (`YYYY-MM-DD`) |

---

## Prochain Grand Prix

```
GET /api/v1/next?year=2026
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int (1950–2100) | année courante | Saison |

**Réponse :** même structure qu'une entrée de `cal`.

```json
{
  "next": {
    "rnd": 18,
    "name": "United States Grand Prix",
    "date": "2026-10-25"
  }
}
```

> **Comportement :** la comparaison se fait sur la date (UTC) uniquement.
> Un GP qui a lieu aujourd'hui reste donc « next » jusqu'à minuit UTC,
> même si la course est terminée.
>
> **Hors saison :** si tous les rounds de la saison sont passés et qu'aucune
> année n'est explicitement demandée, le **1er GP de la saison suivante** est
> renvoyé (fallback sur le dernier GP de la saison si le calendrier N+1 est
> indisponible). Avec `?year=` explicite, le dernier round de cette saison
> est renvoyé.

---

## Classement pilotes

```
GET /api/v1/standings?year=2026&round=20
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int (1950–2100) | année courante | Saison |
| `round` | int (1–30) | dernier round connu | Classement après le round N |

**Réponse :**

```json
{
  "drv": [
    {
      "pos": 1,
      "name": "A. Antonelli",
      "pts": 340
    }
  ]
}
```

| Champ | Type | Description |
|---|---|---|
| `pos` | int | Position au classement |
| `name` | string | Initiale du prénom + nom (`M. Verstappen`) |
| `pts` | int | Points |

---

## Codes d'erreur

| Code | Signification |
|---|---|
| 200 | OK |
| 404 | Endpoint inconnu |
| 422 | Paramètre invalide (`year` hors 1950–2100, `round` hors 1–30) |
| 429 | Rate limit dépassé |
| 503 | Erreur API F1 amont |

**429 :**

```json
{
  "err": "rate_limit",
  "msg": "Trop de requêtes, réessaie dans quelques secondes"
}
```

**503 :** le détail de l'erreur amont n'est jamais exposé au client (il est dans les logs du serveur).

```json
{
  "detail": "Service F1 temporairement indisponible"
}
```

---

## Documentation interactive (Swagger)

**Désactivée par défaut.** Pour l'activer, définir la variable d'environnement :

```
F1_ENABLE_DOCS=1
```

Puis : `http://<serveur>:8000/docs`
