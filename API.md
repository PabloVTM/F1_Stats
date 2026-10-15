# API F1 Stats — Documentation

Base URL : `http://<serveur>:8000`

Toutes les réponses sont en JSON. Les champs utilisent des clés courtes pour minimiser la taille à parser par l'ESP32.

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
| `ts` | string | Timestamp ISO 8601 |

---

## Calendrier

```
GET /api/v1/calendar?year=2026
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int | année courante | Saison souhaitée |

**Réponse :**

```json
{
  "cal": [
    {
      "rnd": 1,
      "name": "Australian Grand Prix",
      "date": "2026-03-08T04:00:00+00:00",
      "sessions": {
        "fp1": "2026-03-06T01:30:00+00:00",
        "fp2": "2026-03-06T05:00:00+00:00",
        "fp3": "2026-03-07T01:30:00+00:00",
        "qual": "2026-03-07T05:00:00+00:00",
        "race": "2026-03-08T04:00:00+00:00"
      }
    }
  ]
}
```

| Champ | Type | Description |
|---|---|---|
| `rnd` | int | Numéro du round |
| `name` | string | Nom du Grand Prix |
| `date` | string | Date/heure de la course (ISO 8601) |
| `sessions` | object | Toutes les séances du weekend |

**Sessions possibles :**

| Clé | Séance |
|---|---|
| `fp1` | Essais libres 1 |
| `fp2` | Essais libres 2 |
| `fp3` | Essais libres 3 |
| `qual` | Qualifications |
| `sprint` | Sprint (weekend sprint seulement) |
| `sq` | Qualifs du sprint (weekend sprint seulement) |
| `race` | Course |

---

## Prochain weekend

```
GET /api/v1/next?year=2026
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int | année courante | Saison |

**Réponse :** idem calendrier mais pour un seul round.

```json
{
  "next": {
    "rnd": 18,
    "name": "United States Grand Prix",
    "date": "2026-10-25T20:00:00+00:00",
    "sessions": {
      "fp1": "2026-10-23T17:30:00+00:00",
      "fp2": "2026-10-23T21:00:00+00:00",
      "fp3": "2026-10-24T17:30:00+00:00",
      "qual": "2026-10-24T21:00:00+00:00",
      "race": "2026-10-25T20:00:00+00:00"
    }
  }
}
```

---

## Classement pilotes

```
GET /api/v1/standings/drivers?year=2026&round=20
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int | année courante | Saison |
| `round` | int | dernier round connu | Arrêter au round N |

**Réponse :**

```json
{
  "drv": [
    {
      "pos": 1,
      "name": "Andrea Kimi Antonelli",
      "team": "Mercedes",
      "pts": 340
    }
  ]
}
```

| Champ | Type | Description |
|---|---|---|
| `pos` | int | Position au classement |
| `name` | string | Prénom + Nom |
| `team` | string | Équipe |
| `pts` | int | Points |

---

## Classement constructeurs

```
GET /api/v1/standings/constructors?year=2026&round=20
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int | année courante | Saison |
| `round` | int | dernier round connu | Arrêter au round N |

**Réponse :**

```json
{
  "con": [
    {
      "pos": 1,
      "name": "Mercedes",
      "pts": 478
    }
  ]
}
```

| Champ | Type | Description |
|---|---|---|
| `pos` | int | Position |
| `name` | string | Nom de l'écurie |
| `pts` | int | Points |

---

## Résultats d'une course

```
GET /api/v1/results/race?year=2026&round=17
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int | année courante | Saison |
| `round` | int | *obligatoire* | Numéro du round |

**Réponse :**

```json
{
  "res": [
    {
      "pos": 1,
      "code": "VER",
      "name": "Max Verstappen",
      "team": "Red Bull",
      "grid": 1,
      "laps": 62,
      "status": "Finished",
      "time": "1:42:00.785"
    },
    {
      "pos": 2,
      "code": "LEC",
      "name": "Charles Leclerc",
      "team": "Ferrari",
      "grid": 2,
      "laps": 62,
      "status": "Finished",
      "time": "+7.335"
    }
  ]
}
```

| Champ | Type | Description |
|---|---|---|
| `pos` | int | Position d'arrivée |
| `code` | string | Code pilote |
| `name` | string | Pilote |
| `team` | string | Équipe |
| `grid` | int | Position de départ |
| `laps` | int | Tours parcourus |
| `status` | string | Statut (Finished / DNF / DNS / …) |
| `time` | string | Temps total ou écart au leader |

---

## Résultats des qualifications

```
GET /api/v1/results/qualifying?year=2026&round=17
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int | année courante | Saison |
| `round` | int | *obligatoire* | Numéro du round |

**Réponse :**

```json
{
  "qual": [
    {
      "pos": 1,
      "code": "VER",
      "name": "Max Verstappen",
      "team": "Red Bull",
      "q1": "1:32.165",
      "q2": "1:31.782",
      "q3": "1:31.056"
    }
  ]
}
```

| Champ | Type | Description |
|---|---|---|
| `pos` | int | Position |
| `code` | string | Code pilote |
| `name` | string | Pilote |
| `team` | string | Équipe |
| `q1` | string | Temps Q1 (vide si pas de temps) |
| `q2` | string | Temps Q2 (vide si éliminé) |
| `q3` | string | Temps Q3 (vide si éliminé) |

---

## Résultats du sprint

```
GET /api/v1/results/sprint?year=2026&round=17
```

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `year` | int | année courante | Saison |
| `round` | int | *obligatoire* | Numéro du round |

**Réponse :** identique à `results/race`.

---

## Codes d'erreur

| Code | Signification |
|---|---|
| 200 | OK |
| 404 | Endpoint inconnu |
| 503 | Erreur API F1 amont (hors ligne ?) |

Les erreurs 503 renvoient :

```json
{
  "detail": "Erreur API F1: <message>"
}
```

---

## Document interactive (Swagger)

FastAPI génère automatiquement une doc interactive :

```
http://<serveur>:8000/docs
```