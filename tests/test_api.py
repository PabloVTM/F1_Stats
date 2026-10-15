from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "ts" in body


def test_calendar():
    resp = client.get("/api/v1/calendar")
    assert resp.status_code == 200
    body = resp.json()
    assert "cal" in body
    assert len(body["cal"]) > 0
    r = body["cal"][0]
    assert "rnd" in r
    assert "name" in r
    assert "date" in r


def test_driver_standings():
    resp = client.get("/api/v1/standings")
    assert resp.status_code == 200
    body = resp.json()
    assert "drv" in body
    assert len(body["drv"]) > 0
    d = body["drv"][0]
    assert "pos" in d
    assert "name" in d
    assert "pts" in d
    assert "team" not in d


def test_constructor_standings():
    resp = client.get("/api/v1/standings/constructors")
    assert resp.status_code == 404


def test_next():
    resp = client.get("/api/v1/next")
    assert resp.status_code == 200
    body = resp.json()
    assert "next" in body


def test_404():
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code == 404