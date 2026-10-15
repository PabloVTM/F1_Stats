from __future__ import annotations

import pytest

from server.f1_client import BASE_URL, cache

# ── Payloads réalistes de l'API jolpica (structure Ergast) ───────────────────

CALENDAR_PAYLOAD = {
    "MRData": {
        "RaceTable": {
            "Races": [
                {
                    "round": "1",
                    # Espace trailing volontaire : teste le .strip()
                    "raceName": "Past Grand Prix ",
                    "date": "2020-03-08",
                },
                {
                    "round": "2",
                    "raceName": "Future Grand Prix",
                    "date": "2099-10-25",
                },
            ]
        }
    }
}

PAST_ONLY_CALENDAR_PAYLOAD = {
    "MRData": {
        "RaceTable": {
            "Races": [
                {
                    "round": "1",
                    "raceName": "Old Grand Prix",
                    "date": "2020-03-08",
                },
            ]
        }
    }
}

NEXT_SEASON_CALENDAR_PAYLOAD = {
    "MRData": {
        "RaceTable": {
            "Races": [
                {
                    "round": "1",
                    "raceName": "Season Opener",
                    "date": "2099-03-01",
                },
            ]
        }
    }
}

STANDINGS_PAYLOAD = {
    "MRData": {
        "StandingsTable": {
            "StandingsLists": [
                {
                    "DriverStandings": [
                        {
                            "position": "1",
                            "points": "340",
                            "Driver": {
                                "givenName": "Andrea Kimi",
                                "familyName": "Antonelli",
                            },
                        },
                        {
                            "position": "2",
                            "points": "300",
                            "Driver": {
                                "givenName": "Max",
                                "familyName": "Verstappen",
                            },
                        },
                    ]
                }
            ]
        }
    }
}


# ── Helpers URL ───────────────────────────────────────────────────────────────


def calendar_url(year: int) -> str:
    return f"{BASE_URL}/{year}.json?limit=30"


def standings_url(year: int) -> str:
    return f"{BASE_URL}/{year}/driverStandings.json?limit=40"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_cache():
    """Chaque test part d'un cache vide (isolation)."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def fast_retry_sleep(monkeypatch):
    """Neutralise le backoff des retries (tests instantanés)."""

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("server.f1_client._sleep", _no_sleep)
