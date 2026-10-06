"""Tests for database client creation, credential fallback and row paging."""

from types import SimpleNamespace

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


def test_count_transactions_asks_for_an_exact_count(monkeypatch):
    """Row caps must not hide rows: counting goes through the count param."""
    log: list[tuple] = []

    class _Query:
        def select(self, columns: str = "*", count: str | None = None):
            log.append(("select", columns, count))
            return self

        def eq(self, column: str, value: object):
            log.append(("eq", column, value))
            return self

        def gte(self, column: str, value: object):
            log.append(("gte", column, value))
            return self

        def lte(self, column: str, value: object):
            log.append(("lte", column, value))
            return self

        def limit(self, value: int):
            log.append(("limit", value))
            return self

        def execute(self):
            return SimpleNamespace(count=1579, data=[{"id": "only-row"}])

    class _Client:
        def table(self, name: str):
            log.append(("table", name))
            return _Query()

    monkeypatch.setattr(database, "get_supabase_client", lambda: _Client())

    total = database.count_transactions(movement_type="gasto", account="Fiwind")

    assert total == 1579
    assert ("select", "id", "exact") in log
    assert ("eq", "movement_type", "gasto") in log
    assert ("eq", "account", "Fiwind") in log


def test_get_all_transactions_pages_past_the_row_cap(monkeypatch):
    """Supabase returns at most 1000 rows per request, whatever limit says."""
    calls: list[int] = []

    def fake_get_transactions(skip: int = 0, limit: int = 100, **kwargs):
        calls.append(skip)
        if skip == 0:
            return [{"id": i} for i in range(1000)]
        if skip == 1000:
            return [{"id": 1000}]
        return []

    monkeypatch.setattr(database, "get_transactions", fake_get_transactions)

    rows = database.get_all_transactions()

    assert [row["id"] for row in rows[-2:]] == [999, 1000]
    assert calls == [0, 1000]


def test_get_all_transactions_stops_on_an_exact_page_boundary(monkeypatch):
    def fake_get_transactions(skip: int = 0, limit: int = 100, **kwargs):
        if skip == 0:
            return [{"id": i} for i in range(1000)]
        return []

    monkeypatch.setattr(database, "get_transactions", fake_get_transactions)

    assert len(database.get_all_transactions()) == 1000
