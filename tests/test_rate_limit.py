from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.rate_limit import RateLimitMiddleware


def _make_app(max_requests: int = 3) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware, max_requests=max_requests, window_seconds=60
    )

    @app.get("/api/v1/ping")
    async def ping():
        return {"ok": True}

    @app.get("/api/v1/health")
    async def health():
        return {"ok": True}

    return app


def test_rate_limit_triggers_429():
    c = TestClient(_make_app(max_requests=3))
    for _ in range(3):
        assert c.get("/api/v1/ping").status_code == 200
    resp = c.get("/api/v1/ping")
    assert resp.status_code == 429
    assert resp.json()["err"] == "rate_limit"


def test_rate_limit_isolated_by_forwarded_for():
    c = TestClient(_make_app(max_requests=2))
    ip1 = {"X-Forwarded-For": "1.2.3.4"}
    ip2 = {"X-Forwarded-For": "5.6.7.8"}
    assert c.get("/api/v1/ping", headers=ip1).status_code == 200
    assert c.get("/api/v1/ping", headers=ip1).status_code == 200
    assert c.get("/api/v1/ping", headers=ip1).status_code == 429
    # Une autre IP (via le proxy) n'est pas affectée
    assert c.get("/api/v1/ping", headers=ip2).status_code == 200


def test_forwarded_for_takes_first_ip():
    c = TestClient(_make_app(max_requests=1))
    headers = {"X-Forwarded-For": "9.9.9.9, 10.0.0.1"}
    assert c.get("/api/v1/ping", headers=headers).status_code == 200
    assert c.get("/api/v1/ping", headers=headers).status_code == 429


def test_health_excluded_from_rate_limit():
    c = TestClient(_make_app(max_requests=1))
    for _ in range(10):
        assert c.get("/api/v1/health").status_code == 200


def test_sweep_removes_inactive_ips():
    mw = RateLimitMiddleware(app=FastAPI(), max_requests=10, window_seconds=60)
    mw._store = {
        "1.1.1.1": [0.0],      # ancien → à purger
        "2.2.2.2": [1000.0],   # récent → à garder
        "3.3.3.3": [],         # vide → à purger
    }
    mw._sweep(now=1001.0)  # cutoff = 941
    assert "1.1.1.1" not in mw._store
    assert "2.2.2.2" in mw._store
    assert "3.3.3.3" not in mw._store
