from __future__ import annotations

from datetime import UTC, datetime

import httpx
from fastapi.testclient import TestClient

from server.main import app
from tests.conftest import (
    CALENDAR_PAYLOAD,
    NEXT_SEASON_CALENDAR_PAYLOAD,
    PAST_ONLY_CALENDAR_PAYLOAD,
    STANDINGS_PAYLOAD,
    calendar_url,
    standings_url,
)

client = TestClient(app)

YEAR = datetime.now(UTC).year


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "ts" in body


def test_calendar(respx_mock):
    respx_mock.get(calendar_url(YEAR)).mock(
        return_value=httpx.Response(200, json=CALENDAR_PAYLOAD)
    )
    resp = client.get("/api/v1/calendar")
    assert resp.status_code == 200
    cal = resp.json()["cal"]
    assert len(cal) == 2
    assert cal[0] == {"rnd": 1, "name": "Past Grand Prix", "date": "2020-03-08"}
    assert set(cal[0].keys()) == {"rnd", "name", "date"}


def test_driver_standings(respx_mock):
    respx_mock.get(standings_url(YEAR)).mock(
        return_value=httpx.Response(200, json=STANDINGS_PAYLOAD)
    )
    resp = client.get("/api/v1/standings")
    assert resp.status_code == 200
    drv = resp.json()["drv"]
    assert len(drv) == 2
    assert drv[0] == {"pos": 1, "name": "A. Antonelli", "pts": 340}
    assert drv[1] == {"pos": 2, "name": "M. Verstappen", "pts": 300}
    assert "team" not in drv[0]


def test_next(respx_mock):
    respx_mock.get(calendar_url(YEAR)).mock(
        return_value=httpx.Response(200, json=CALENDAR_PAYLOAD)
    )
    resp = client.get("/api/v1/next")
    assert resp.status_code == 200
    nxt = resp.json()["next"]
    # Le round passé (2020) est ignoré, le futur (2099) est retourné
    assert nxt["name"] == "Future Grand Prix"
    assert nxt["rnd"] == 2


def test_upstream_error_returns_generic_503(respx_mock):
    respx_mock.get(calendar_url(YEAR)).mock(return_value=httpx.Response(500))
    resp = client.get("/api/v1/calendar")
    assert resp.status_code == 503
    # Le détail de l'erreur amont ne doit pas fuiter côté client
    assert resp.json()["detail"] == "Service F1 temporairement indisponible"


def test_cache_dedupes_upstream_calls(respx_mock):
    route = respx_mock.get(calendar_url(YEAR)).mock(
        return_value=httpx.Response(200, json=CALENDAR_PAYLOAD)
    )
    assert client.get("/api/v1/calendar").status_code == 200
    assert client.get("/api/v1/calendar").status_code == 200
    assert route.call_count == 1


def test_invalid_year_returns_422():
    assert client.get("/api/v1/calendar", params={"year": 1800}).status_code == 422
    assert client.get("/api/v1/calendar", params={"year": 2200}).status_code == 422


def test_invalid_round_returns_422():
    assert client.get("/api/v1/standings", params={"round": 0}).status_code == 422
    assert client.get("/api/v1/standings", params={"round": 99}).status_code == 422


def test_next_offseason_rolls_to_next_season(respx_mock):
    """Hors saison : sans année explicite, /next bascule sur le 1er GP de N+1."""
    respx_mock.get(calendar_url(YEAR)).mock(
        return_value=httpx.Response(200, json=PAST_ONLY_CALENDAR_PAYLOAD)
    )
    respx_mock.get(calendar_url(YEAR + 1)).mock(
        return_value=httpx.Response(200, json=NEXT_SEASON_CALENDAR_PAYLOAD)
    )
    resp = client.get("/api/v1/next")
    assert resp.status_code == 200
    assert resp.json()["next"]["name"] == "Season Opener"


def test_next_offseason_explicit_year_stays_in_season(respx_mock):
    """Avec une année explicite, /next reste sur le dernier GP de cette saison."""
    respx_mock.get(calendar_url(2026)).mock(
        return_value=httpx.Response(200, json=PAST_ONLY_CALENDAR_PAYLOAD)
    )
    resp = client.get("/api/v1/next", params={"year": 2026})
    assert resp.status_code == 200
    assert resp.json()["next"]["name"] == "Old Grand Prix"


def test_retry_on_transient_500_then_success(respx_mock):
    route = respx_mock.get(calendar_url(YEAR)).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json=CALENDAR_PAYLOAD),
        ]
    )
    resp = client.get("/api/v1/calendar")
    assert resp.status_code == 200
    assert route.call_count == 2


def test_429_exhausts_retries_returns_503(respx_mock):
    route = respx_mock.get(calendar_url(YEAR)).mock(
        return_value=httpx.Response(429)
    )
    resp = client.get("/api/v1/calendar")
    assert resp.status_code == 503
    assert route.call_count == 3


def test_client_error_4xx_no_retry(respx_mock):
    """Un 4xx amont (hors 429) est définitif : pas de retry."""
    route = respx_mock.get(calendar_url(YEAR)).mock(
        return_value=httpx.Response(404)
    )
    resp = client.get("/api/v1/calendar")
    assert resp.status_code == 503
    assert route.call_count == 1


def test_docs_disabled_by_default():
    """Swagger/OpenAPI désactivés sans F1_ENABLE_DOCS."""
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_constructor_standings_removed():
    # Endpoint supprimé dans la v1.1
    assert client.get("/api/v1/standings/constructors").status_code == 404


def test_404():
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code == 404
