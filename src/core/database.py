"""Database connection and CRUD operations for Tarasca using Supabase."""

import os
import sys
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from dotenv import load_dotenv
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
    query = client.table("transactions").select("*")

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

    response = query.order("date", desc=True).range(skip, skip + limit - 1).execute()
    return [cast(dict[str, Any], item) for item in response.data]


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
