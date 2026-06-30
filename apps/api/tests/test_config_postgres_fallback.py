"""
Tests for Vercel-Neon POSTGRES_URL / POSTGRES_URL_NON_POOLING fallback and
'postgres://' → 'postgresql://' scheme normalisation in app.core.config.Settings.
"""
import importlib
import sys
import os
import pytest


def _fresh_settings(monkeypatch, env_overrides: dict) -> object:
    """
    Build a fresh Settings instance with a controlled environment.

    Sets canonical DATABASE_URL vars to "" in the OS env so they win over any
    .env file values (pydantic_settings gives env vars higher priority than
    env_file), then applies env_overrides, then re-imports config so
    pydantic_settings re-reads the patched env.
    """
    # Set to "" so the env-var source wins over the .env file (priority: env > file)
    for key in ("DATABASE_URL", "DATABASE_URL_UNPOOLED",
                "POSTGRES_URL", "POSTGRES_URL_NON_POOLING"):
        monkeypatch.setenv(key, "")

    # Ensure required fields are present
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-unit-tests")

    for k, v in env_overrides.items():
        monkeypatch.setenv(k, v)

    # Force re-import of config module so BaseSettings re-reads the patched env
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    config_mod = importlib.import_module("app.core.config")
    return config_mod.Settings()


class TestPostgresFallback:
    def test_postgres_url_fallback_and_scheme_normalised(self, monkeypatch):
        """POSTGRES_URL with 'postgres://' scheme → DATABASE_URL normalised to 'postgresql://'."""
        settings = _fresh_settings(monkeypatch, {
            "POSTGRES_URL": "postgres://u:p@host/db",
        })
        assert settings.DATABASE_URL == "postgresql://u:p@host/db"

    def test_postgres_url_non_pooling_fallback_and_scheme_normalised(self, monkeypatch):
        """POSTGRES_URL_NON_POOLING → DATABASE_URL_UNPOOLED normalised."""
        settings = _fresh_settings(monkeypatch, {
            "POSTGRES_URL": "postgres://u:p@host/db",
            "POSTGRES_URL_NON_POOLING": "postgres://u:p@host-np/db",
        })
        assert settings.DATABASE_URL_UNPOOLED == "postgresql://u:p@host-np/db"

    def test_canonical_database_url_takes_priority(self, monkeypatch):
        """When DATABASE_URL is already set, POSTGRES_URL is ignored."""
        settings = _fresh_settings(monkeypatch, {
            "DATABASE_URL": "postgresql://canonical:pass@host/db",
            "POSTGRES_URL": "postgres://should-be-ignored/db",
        })
        assert settings.DATABASE_URL == "postgresql://canonical:pass@host/db"

    def test_already_postgresql_scheme_untouched(self, monkeypatch):
        """'postgresql://' prefix is left unchanged (no double-replacement)."""
        settings = _fresh_settings(monkeypatch, {
            "POSTGRES_URL": "postgresql://u:p@host/db",
        })
        assert settings.DATABASE_URL == "postgresql://u:p@host/db"

    def test_postgresql_plus_driver_scheme_untouched(self, monkeypatch):
        """'postgresql+asyncpg://' driver variant is not altered."""
        settings = _fresh_settings(monkeypatch, {
            "DATABASE_URL": "postgresql+asyncpg://u:p@host/db",
        })
        assert settings.DATABASE_URL == "postgresql+asyncpg://u:p@host/db"
