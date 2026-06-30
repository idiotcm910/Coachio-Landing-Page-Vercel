"""TDD: cron dispatch endpoint — CRON_SECRET gate (401 vs 200), one dispatch pass."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.v1.endpoints.cron.dispatch_broadcasts as mod


def _client(monkeypatch, secret="topsecret"):
    monkeypatch.setattr(mod.settings, "CRON_SECRET", secret)
    monkeypatch.setattr(
        mod, "run_once_in_session",
        lambda **kw: {"promoted": 1, "dispatched": 0, "reaped": 0, "sent": 3},
    )
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/v1/cron")
    return TestClient(app)


def test_missing_secret_returns_401(monkeypatch):
    c = _client(monkeypatch)
    assert c.get("/api/v1/cron/dispatch-broadcasts").status_code == 401


def test_wrong_secret_returns_401(monkeypatch):
    c = _client(monkeypatch)
    r = c.get("/api/v1/cron/dispatch-broadcasts", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_bearer_secret_runs_and_returns_counts(monkeypatch):
    c = _client(monkeypatch)
    r = c.get("/api/v1/cron/dispatch-broadcasts", headers={"Authorization": "Bearer topsecret"})
    assert r.status_code == 200
    assert r.json()["sent"] == 3


def test_query_secret_also_works(monkeypatch):
    c = _client(monkeypatch)
    r = c.post("/api/v1/cron/dispatch-broadcasts?secret=topsecret")
    assert r.status_code == 200
    assert r.json()["promoted"] == 1


def test_empty_configured_secret_refuses(monkeypatch):
    c = _client(monkeypatch, secret="")
    r = c.get("/api/v1/cron/dispatch-broadcasts", headers={"Authorization": "Bearer "})
    assert r.status_code == 401
