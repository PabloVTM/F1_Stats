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


def _parse_dt(date: str, time: str | None = None) -> str:
    if not time:
        return date
    try:
        dt = datetime.fromisoformat(f"{date}T{time}")
        return dt.isoformat()
    except ValueError:
        return date


# ── Calendar ──────────────────────────────────────────────────────────────────


async def get_calendar(year: int | None = None) -> list[dict[str, Any]]:
    year = year or _current_year()
    mrdata = await _fetch_mrdata(f"{year}.json?limit=30")
    races = (mrdata.get("RaceTable") or {}).get("Races", [])

    result = []
    for r in races:
        sessions = {
            "fp1": _parse_dt(
                (r.get("FirstPractice") or {}).get("date", ""),
                (r.get("FirstPractice") or {}).get("time"),
            ),
            "fp2": _parse_dt(
                (r.get("SecondPractice") or {}).get("date", ""),
                (r.get("SecondPractice") or {}).get("time"),
            ),
            "fp3": _parse_dt(
                (r.get("ThirdPractice") or {}).get("date", ""),
                (r.get("ThirdPractice") or {}).get("time"),
            ),
            "qual": _parse_dt(
                (r.get("Qualifying") or {}).get("date", ""),
                (r.get("Qualifying") or {}).get("time"),
            ),
        }
        if r.get("Sprint"):
            sessions["sprint"] = _parse_dt(
                r["Sprint"].get("date", ""), r["Sprint"].get("time")
            )
        if r.get("SprintQualifying"):
            sessions["sq"] = _parse_dt(
                r["SprintQualifying"].get("date", ""),
                r["SprintQualifying"].get("time"),
            )

        race_dt = _parse_dt(r.get("date", ""), r.get("time"))

        sessions["race"] = race_dt

        result.append(
            {
                "rnd": _to_int(r.get("round", 0)),
                "name": r.get("raceName", ""),
                "date": race_dt,
                "sessions": {k: v for k, v in sessions.items() if v},
            }
        )
    return result


# ── Current / Next Race ───────────────────────────────────────────────────────


async def get_current_weekend(year: int | None = None) -> dict[str, Any] | None:
    calendar = await get_calendar(year)
    now = _now()
    current_year = _current_year()

    future = [r for r in calendar if r["date"] > now.isoformat() or r["date"] > now.strftime('%Y-%m-%d')]
    if not future:
        return None
    return future[0]


# ── Driver Standings ──────────────────────────────────────────────────────────


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
                "name": driver.get("familyName", ""),
                "team": (s.get("Constructors") or [{}])[0].get("name", ""),
                "pts": _to_int(s.get("points", 0)),
            }
        )
    return result


# ── Constructor Standings ─────────────────────────────────────────────────────


async def get_constructor_standings(
    year: int | None = None, round_num: int | None = None
) -> list[dict[str, Any]]:
    year = year or _current_year()
    path = f"{year}/constructorStandings.json?limit=40"
    if round_num:
        path = f"{year}/{round_num}/constructorStandings.json?limit=40"

    mrdata = await _fetch_mrdata(path)
    standings = (
        (mrdata.get("StandingsTable") or {}).get("StandingsLists") or [{}]
    )[0].get("ConstructorStandings", [])

    result = []
    for s in standings:
        constructor = s.get("Constructor", {})
        result.append(
            {
                "pos": _to_int(s.get("position", 0)),
                "name": constructor.get("name", ""),
                "pts": _to_int(s.get("points", 0)),
            }
        )
    return result


# ── Race Results ──────────────────────────────────────────────────────────────


async def get_race_results(
    year: int | None = None, round_num: int | None = None
) -> list[dict[str, Any]]:
    year = year or _current_year()
    round_num = round_num or 1
    mrdata = await _fetch_mrdata(f"{year}/{round_num}/results.json?limit=40")
    races = (mrdata.get("RaceTable") or {}).get("Races", [])
    if not races:
        return []
    results = races[0].get("Results", [])

    result = []
    for r in results:
        driver = r.get("Driver", {})
        result.append(
            {
                "pos": _to_int(r.get("position", 0)),
                "code": driver.get("code", ""),
                "name": driver.get("familyName", ""),
                "team": (r.get("Constructor") or {}).get("name", ""),
                "grid": _to_int(r.get("grid", 0)),
                "laps": _to_int(r.get("laps", 0)),
                "status": r.get("status", ""),
                "time": (
                    (r.get("Time") or {}).get("time", "")
                    if r.get("Time")
                    else ""
                ),
            }
        )
    return result


# ── Qualifying Results ────────────────────────────────────────────────────────


async def get_qualifying_results(
    year: int | None = None, round_num: int | None = None
) -> list[dict[str, Any]]:
    year = year or _current_year()
    round_num = round_num or 1
    mrdata = await _fetch_mrdata(f"{year}/{round_num}/qualifying.json?limit=40")
    races = (mrdata.get("RaceTable") or {}).get("Races", [])
    if not races:
        return []
    results = races[0].get("QualifyingResults", [])

    result = []
    for r in results:
        driver = r.get("Driver", {})
        result.append(
            {
                "pos": _to_int(r.get("position", 0)),
                "code": driver.get("code", ""),
                "name": driver.get("familyName", ""),
                "team": (r.get("Constructor") or {}).get("name", ""),
                "q1": r.get("q1", ""),
                "q2": r.get("q2", ""),
                "q3": r.get("q3", ""),
            }
        )
    return result


# ── Sprint Results ────────────────────────────────────────────────────────────


async def get_sprint_results(
    year: int | None = None, round_num: int | None = None
) -> list[dict[str, Any]]:
    year = year or _current_year()
    round_num = round_num or 1
    mrdata = await _fetch_mrdata(f"{year}/{round_num}/sprint.json?limit=40")
    races = (mrdata.get("RaceTable") or {}).get("Races", [])
    if not races:
        return []
    results = races[0].get("SprintResults", [])

    result = []
    for r in results:
        driver = r.get("Driver", {})
        result.append(
            {
                "pos": _to_int(r.get("position", 0)),
                "code": driver.get("code", ""),
                "name": driver.get("familyName", ""),
                "team": (r.get("Constructor") or {}).get("name", ""),
                "grid": _to_int(r.get("grid", 0)),
                "laps": _to_int(r.get("laps", 0)),
                "status": r.get("status", ""),
                "time": (
                    (r.get("Time") or {}).get("time", "")
                    if r.get("Time")
                    else ""
                ),
            }
        )
    return result