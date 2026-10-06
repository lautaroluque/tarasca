"""Database connection and CRUD operations for Tarasca using Supabase."""

import json
import os
import sys
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from dotenv import load_dotenv
from postgrest.types import CountMethod
from supabase import Client, create_client

load_dotenv()

_supabase_client: Client | None = None


def _credentials_from_streamlit_secrets() -> tuple[str | None, str | None]:
    """Read Supabase credentials from Streamlit secrets.

    Returns (None, None) unless Streamlit is already loaded in this process,
    so headless callers (scripts/, CI) never import it. Importing Streamlit
    just to read secrets pulls the framework into headless runs, emits
    config warnings, and can leave background threads behind.
    """
    if "streamlit" not in sys.modules:
        return None, None

    import streamlit as st

    if not st.runtime.exists():
        return None, None

    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["secret_key"]
    except Exception:
        return None, None

    return url, key


def get_supabase_client() -> Client:
    """Get or create Supabase client."""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    # Try Streamlit secrets first (app runtime), then environment variables
    # (headless scripts, CI).
    url, key = _credentials_from_streamlit_secrets()
    if not url or not key:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SECRET_KEY")

    if not url or not key:
        raise ValueError(
            "Supabase credentials not found. Set SUPABASE_URL and SUPABASE_SECRET_KEY "
            "environment variables or configure Streamlit secrets."
        )

    _supabase_client = create_client(url, key)
    return _supabase_client


def create_db_and_tables() -> None:
    """Create database tables.

    Note: This is handled by Supabase migrations. This function is a no-op
    when using Supabase.
    """
    pass


# Category CRUD


def get_categories() -> list[dict[str, Any]]:
    """Get all categories."""
    client = get_supabase_client()
    response = client.table("categories").select("*").execute()
    return [cast(dict[str, Any], item) for item in response.data]


def get_category_by_id(category_id: UUID) -> dict[str, Any] | None:
    """Get category by ID."""
    client = get_supabase_client()
    response = client.table("categories").select("*").eq("id", str(category_id)).execute()
    return cast(dict[str, Any], response.data[0]) if response.data else None


def create_category(category_data: dict) -> dict[str, Any]:
    """Create a new category."""
    client = get_supabase_client()
    response = client.table("categories").insert(category_data).execute()
    return cast(dict[str, Any], response.data[0])


# Transaction CRUD


def _transaction_query(
    client: Client,
    *,
    columns: str = "*",
    count: CountMethod | None = None,
    category_id: UUID | None = None,
    account: str | None = None,
    currency: str | None = None,
    movement_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Any:
    """Build a filtered (unordered) transactions query."""
    query = client.table("transactions").select(columns, count=count)

    if category_id:
        query = query.eq("category_id", str(category_id))
    if account:
        query = query.eq("account", account)
    if currency:
        query = query.eq("currency", currency)
    if movement_type:
        query = query.eq("movement_type", movement_type)
    if start_date:
        query = query.gte("date", start_date.isoformat())
    if end_date:
        query = query.lte("date", end_date.isoformat())
    return query


def get_transactions(
    skip: int = 0,
    limit: int = 100,
    category_id: UUID | None = None,
    account: str | None = None,
    currency: str | None = None,
    movement_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Get transactions with optional filters."""
    client = get_supabase_client()
    query = _transaction_query(
        client,
        category_id=category_id,
        account=account,
        currency=currency,
        movement_type=movement_type,
        start_date=start_date,
        end_date=end_date,
    )
    response = query.order("date", desc=True).range(skip, skip + limit - 1).execute()
    return [cast(dict[str, Any], item) for item in response.data]


def count_transactions(
    category_id: UUID | None = None,
    account: str | None = None,
    currency: str | None = None,
    movement_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """Count transactions matching the filters (not capped by row limits)."""
    client = get_supabase_client()
    query = _transaction_query(
        client,
        columns="id",
        count=CountMethod.exact,
        category_id=category_id,
        account=account,
        currency=currency,
        movement_type=movement_type,
        start_date=start_date,
        end_date=end_date,
    )
    response = query.limit(1).execute()
    return int(response.count or 0)


def get_all_transactions(
    category_id: UUID | None = None,
    account: str | None = None,
    currency: str | None = None,
    movement_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Get every transaction matching the filters, however many there are.

    Supabase's API caps rows returned per request at 1000 no matter what
    ``limit`` asks for, so a single ``limit=10000`` silently truncates. Page
    through ``range()`` until a page comes back short instead.
    """
    page_size = 1000
    rows: list[dict[str, Any]] = []
    skip = 0
    while True:
        page = get_transactions(
            skip=skip,
            limit=page_size,
            category_id=category_id,
            account=account,
            currency=currency,
            movement_type=movement_type,
            start_date=start_date,
            end_date=end_date,
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        skip += page_size


def get_transaction_by_id(transaction_id: UUID) -> dict[str, Any] | None:
    """Get transaction by ID."""
    client = get_supabase_client()
    response = (
        client.table("transactions").select("*").eq("id", str(transaction_id)).execute()
    )
    return cast(dict[str, Any], response.data[0]) if response.data else None


def create_transaction(transaction_data: dict) -> dict[str, Any]:
    """Create a new transaction."""
    client = get_supabase_client()
    response = client.table("transactions").insert(transaction_data).execute()
    return cast(dict[str, Any], response.data[0])


def create_transactions_bulk(transactions_data: list[dict]) -> int:
    """Create multiple transactions in bulk."""
    client = get_supabase_client()
    response = client.table("transactions").insert(transactions_data).execute()
    return len(response.data)


def update_transaction(
    transaction_id: UUID, update_data: dict
) -> dict[str, Any] | None:
    """Update an existing transaction."""
    client = get_supabase_client()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    response = (
        client.table("transactions")
        .update(update_data)
        .eq("id", str(transaction_id))
        .execute()
    )
    return cast(dict[str, Any], response.data[0]) if response.data else None


def delete_transaction(transaction_id: UUID) -> bool:
    """Delete a transaction."""
    client = get_supabase_client()
    response = (
        client.table("transactions").delete().eq("id", str(transaction_id)).execute()
    )
    return len(response.data) > 0


# Budget CRUD


def get_budgets(
    month: int | None = None,
    year: int | None = None,
) -> list[dict[str, Any]]:
    """Get budgets with optional filters."""
    client = get_supabase_client()
    query = client.table("budgets").select("*")

    if month:
        query = query.eq("month", month)
    if year:
        query = query.eq("year", year)

    response = query.execute()
    return [cast(dict[str, Any], item) for item in response.data]


def get_budget_by_id(budget_id: UUID) -> dict[str, Any] | None:
    """Get budget by ID."""
    client = get_supabase_client()
    response = client.table("budgets").select("*").eq("id", str(budget_id)).execute()
    return cast(dict[str, Any], response.data[0]) if response.data else None


def create_budget(budget_data: dict) -> dict[str, Any]:
    """Create a new budget."""
    client = get_supabase_client()
    response = client.table("budgets").insert(budget_data).execute()
    return cast(dict[str, Any], response.data[0])


def update_budget(budget_id: UUID, update_data: dict) -> dict[str, Any] | None:
    """Update an existing budget."""
    client = get_supabase_client()
    response = (
        client.table("budgets")
        .update(update_data)
        .eq("id", str(budget_id))
        .execute()
    )
    return cast(dict[str, Any], response.data[0]) if response.data else None


def delete_budget(budget_id: UUID) -> bool:
    """Delete a budget."""
    client = get_supabase_client()
    response = client.table("budgets").delete().eq("id", str(budget_id)).execute()
    return len(response.data) > 0


# Key/value app settings
#
# Stored in `ingest_state`, the only key/value table in the schema (migration
# 004). The email poller owns the `imap_*` keys; anything else here is app
# state such as the opening balances used for the combined balance view.


def get_setting(key: str) -> str | None:
    """Read a value from the settings key/value store."""
    client = get_supabase_client()
    response = client.table("ingest_state").select("value").eq("key", key).execute()
    if response.data:
        return str(cast(dict[str, Any], response.data[0]).get("value"))
    return None


def set_setting(key: str, value: str) -> None:
    """Write a value to the settings key/value store (upsert)."""
    client = get_supabase_client()
    client.table("ingest_state").upsert({"key": key, "value": value}).execute()


def get_setting_json(key: str, default: Any) -> Any:
    """Read a JSON-encoded setting, falling back to ``default``."""
    raw = get_setting(key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def set_setting_json(key: str, value: Any) -> None:
    """Write a JSON-encoded setting."""
    set_setting(key, json.dumps(value, ensure_ascii=False))
