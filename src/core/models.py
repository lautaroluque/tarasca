"""Data models for Tarasca."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class CategoryBase(BaseModel):
    """Base category model."""

    name: str
    color: str = "#808080"
    icon: str = "📦"


class Category(CategoryBase, SQLModel, table=True):
    """Category database model."""

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)


class TransactionBase(BaseModel):
    """Base transaction model."""

    date: datetime
    description: str
    amount: float  # signed: positive = money in, negative = money out
    currency: str = Field(default="ARS")  # ARS, USD, USDT, USDC...
    movement_type: str = Field(default="gasto", pattern="^(ingreso|gasto|transferencia)$")
    account: str
    category_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Transaction(TransactionBase, SQLModel, table=True):
    """Transaction database model."""

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    updated_at: datetime = SQLField(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))  # type: ignore


class TransactionCreate(TransactionBase):
    """Model for creating a new transaction."""

    pass


class TransactionUpdate(BaseModel):
    """Model for updating an existing transaction."""

    date: datetime | None = None
    description: str | None = None
    amount: float | None = None
    currency: str | None = None
    movement_type: str | None = None
    account: str | None = None
    category_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class BudgetBase(BaseModel):
    """Base budget model."""

    category_id: UUID
    amount: float
    currency: str = Field(default="ARS", pattern="^(ARS|USD)$")
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)


class Budget(BudgetBase, SQLModel, table=True):
    """Budget database model."""

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)


class BudgetCreate(BudgetBase):
    """Model for creating a new budget."""

    pass


class BudgetUpdate(BaseModel):
    """Model for updating an existing budget."""

    amount: float | None = None
    month: int | None = None
    year: int | None = None
