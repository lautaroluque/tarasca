"""Tests for database client creation and credential fallback."""

from src.core import database
from src.core.database import get_supabase_client


def test_get_supabase_client_falls_back_to_env_vars(tmp_path, monkeypatch):
    """Headless/CI runs have no .streamlit/secrets.toml → env vars must work."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-secret-key")
    # Move to an empty directory so st.secrets raises StreamlitSecretNotFoundError
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(database, "_supabase_client", None)

    client = get_supabase_client()

    assert client is not None
    # Second call returns the cached client
    assert get_supabase_client() is client


def test_get_supabase_client_missing_credentials_raises(tmp_path, monkeypatch):
    """No secrets file and no env vars → clear error."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(database, "_supabase_client", None)

    try:
        get_supabase_client()
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "Supabase credentials not found" in str(e)
