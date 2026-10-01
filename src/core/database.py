"""Database connection and CRUD operations for Tarasca."""

import os
from datetime import datetime
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

load_dotenv()


def get_engine():
    """Create database engine."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # For PostgreSQL (Supabase)
    if database_url.startswith("postgresql"):
        return create_engine(database_url, pool_pre_ping=True)

    # For SQLite (local development)
    connect_args = {"check_same_thread": False}
    return create_engine(
        database_url,
        connect_args=connect_args,
        poolclass=StaticPool,
    )


def create_db_and_tables():
    """Create database tables."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session."""
    engine = get_engine()
    with Session(engine) as session:
        yield session


# Category CRUD


def get_categories(session: Session) -> list[Any]:
    """Get all categories."""
    return list(session.exec(select(Category)).all())


def get_category_by_id(session: Session, category_id: UUID) -> Any | None:
    """Get category by ID."""
    return session.get(Category, category_id)


def create_category(session: Session, category_data: dict) -> Any:
    """Create a new category."""
    category = Category(**category_data)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


# Transaction CRUD


def get_transactions(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    category_id: UUID | None = None,
    account: str | None = None,
    currency: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Any]:
    """Get transactions with optional filters."""
    statement = select(Transaction)

    if category_id:
        statement = statement.where(Transaction.category_id == category_id)
    if account:
        statement = statement.where(Transaction.account == account)
    if currency:
        statement = statement.where(Transaction.currency == currency)
    if start_date:
        statement = statement.where(Transaction.date >= start_date)
    if end_date:
        statement = statement.where(Transaction.date <= end_date)

    statement = statement.order_by(Transaction.date.desc()).offset(skip).limit(limit)  # type: ignore[attr-defined]
    return list(session.exec(statement).all())


def get_transaction_by_id(session: Session, transaction_id: UUID) -> Any | None:
    """Get transaction by ID."""
    return session.get(Transaction, transaction_id)


def create_transaction(session: Session, transaction_data: dict) -> Any:
    """Create a new transaction."""
    transaction = Transaction(**transaction_data)
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def create_transactions_bulk(session: Session, transactions_data: list[dict]) -> int:
    """Create multiple transactions in bulk."""
    transactions = [Transaction(**data) for data in transactions_data]
    session.add_all(transactions)
    session.commit()
    return len(transactions)


def update_transaction(
    session: Session, transaction_id: UUID, update_data: dict
) -> Any | None:
    """Update an existing transaction."""
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        return None

    for key, value in update_data.items():
        if value is not None:
            setattr(transaction, key, value)

    transaction.updated_at = datetime.utcnow()
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def delete_transaction(session: Session, transaction_id: UUID) -> bool:
    """Delete a transaction."""
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        return False

    session.delete(transaction)
    session.commit()
    return True


# Budget CRUD


def get_budgets(
    session: Session,
    month: int | None = None,
    year: int | None = None,
) -> list[Any]:
    """Get budgets with optional filters."""
    statement = select(Budget)

    if month:
        statement = statement.where(Budget.month == month)
    if year:
        statement = statement.where(Budget.year == year)

    return list(session.exec(statement).all())


def get_budget_by_id(session: Session, budget_id: UUID) -> Any | None:
    """Get budget by ID."""
    return session.get(Budget, budget_id)


def create_budget(session: Session, budget_data: dict) -> Any:
    """Create a new budget."""
    budget = Budget(**budget_data)
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


def update_budget(session: Session, budget_id: UUID, update_data: dict) -> Any | None:
    """Update an existing budget."""
    budget = session.get(Budget, budget_id)
    if not budget:
        return None

    for key, value in update_data.items():
        if value is not None:
            setattr(budget, key, value)

    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


def delete_budget(session: Session, budget_id: UUID) -> bool:
    """Delete a budget."""
    budget = session.get(Budget, budget_id)
    if not budget:
        return False

    session.delete(budget)
    session.commit()
    return True


# Import models to avoid circular imports
from src.core.models import Budget, Category, Transaction  # noqa: E402
