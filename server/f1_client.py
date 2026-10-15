from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from server.cache import TTLCache

logger = logging.getLogger(__name__)

BASE_URL = "https://api.jolpi.ca/ergast/f1"
TIMEOUT = httpx.Timeout(15.0)

cache = TTLCache()


def _now() -> datetime:
    return datetime.now(UTC)


def _current_year() -> int:
    return _now().year


def _weekend_ttl() -> int:
    return 3600 if _now().weekday() >= 4 else 86400


async def _fetch(path: str) -> dict[str, Any]:
    url = f"{BASE_URL}/{path}"
    cached = cache.get(url)
    if cached:
        return cached
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    cache.set(url, data, ttl=_weekend_ttl())
    return data


async def _fetch_mrdata(path: str) -> dict[str, Any]:
    data = await _fetch(path)
    return data.get("MRData", {})


def _to_int(val: str) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _short_name(given: str, family: str) -> str:
    if given:
        return f"{given[0]}. {family}"
    return family


# ── Calendar ──────────────────────────────────────────────────────────────────


async def get_calendar(year: int | None = None) -> list[dict[str, Any]]:
    year = year or _current_year()
    mrdata = await _fetch_mrdata(f"{year}.json?limit=30")
    races = (mrdata.get("RaceTable") or {}).get("Races", [])

    result = []
    for r in races:
        result.append(
            {
                "rnd": _to_int(r.get("round", 0)),
                "name": r.get("raceName", ""),
                "date": (r.get("date") or "")[:10],
            }
        )
    return result


# ── Current / Next Race ───────────────────────────────────────────────────────


async def get_driver_standings(
    year: int | None = None, round_num: int | None = None
) -> list[dict[str, Any]]:
    year = year or _current_year()
    path = f"{year}/driverStandings.json?limit=40"
    if round_num:
        path = f"{year}/{round_num}/driverStandings.json?limit=40"

    mrdata = await _fetch_mrdata(path)
    standings = (
        (mrdata.get("StandingsTable") or {}).get("StandingsLists") or [{}]
    )[0].get("DriverStandings", [])

    result = []
    for s in standings:
        driver = s.get("Driver", {})
        result.append(
            {
                "pos": _to_int(s.get("position", 0)),
                "name": _short_name(
                    driver.get("givenName", ""), driver.get("familyName", "")
                ),
                "pts": _to_int(s.get("points", 0)),
            }
        )
    return result


# ── Race Results ──────────────────────────────────────────────────────────────

