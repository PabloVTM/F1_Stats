from __future__ import annotations

import server.cache as cache_module
from server.cache import TTLCache


def test_get_set():
    c = TTLCache()
    c.set("a", 1, ttl=60)
    assert c.get("a") == 1


def test_missing_key_returns_none():
    assert TTLCache().get("nope") is None


def test_expired_entry_returns_none(monkeypatch):
    fake_now = [1000.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: fake_now[0])
    c = TTLCache()
    c.set("a", 1, ttl=10)
    assert c.get("a") == 1
    fake_now[0] += 11
    assert c.get("a") is None
    # L'entrée expirée est supprimée du store
    assert "a" not in c._store


def test_maxsize_eviction():
    c = TTLCache(maxsize=2)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)  # store plein → clear puis insertion
    assert c.get("a") is None
    assert c.get("b") is None
    assert c.get("c") == 3


def test_set_purges_expired_before_eviction(monkeypatch):
    fake_now = [0.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: fake_now[0])
    c = TTLCache(default_ttl=10, maxsize=2)
    c.set("a", 1)
    c.set("b", 2)
    fake_now[0] += 11  # a et b expirés
    c.set("c", 3)  # purge des expirés → pas besoin de clear
    assert c.get("c") == 3
    assert len(c._store) == 1


def test_clear():
    c = TTLCache()
    c.set("a", 1)
    c.clear()
    assert c.get("a") is None
