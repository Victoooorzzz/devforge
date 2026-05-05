import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


def now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SystemOutbox(SQLModel, table=True):
    __tablename__ = "system_outbox"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    app_name: Optional[str] = Field(default=None, index=True, max_length=30)
    job_type: Optional[str] = Field(default=None, max_length=50)

    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    status: str = Field(default="pending", index=True, max_length=20)  # pending, processing, completed, failed, dead_letter
    priority: int = Field(default=5)  # 1 urgent, 10 low

    attempts: int = Field(default=0)
    max_attempts: int = Field(default=3)
    next_retry_at: datetime = Field(
        default_factory=now_naive,
        sa_type=DateTime(timezone=False),
        index=True
    )

    locked_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=False),
        index=True
    )
    locked_by: Optional[str] = Field(default=None, max_length=100)

    created_at: datetime = Field(
        default_factory=now_naive,
        sa_type=DateTime(timezone=False),
        index=True
    )
    updated_at: datetime = Field(
        default_factory=now_naive,
        sa_type=DateTime(timezone=False)
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=False)
    )

    result: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    error_message: Optional[str] = Field(default=None)


class InvoiceMagicLink(SQLModel, table=True):
    __tablename__ = "invoice_magic_links"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    token: str = Field(unique=True, index=True, max_length=100)
    invoice_id: str = Field(index=True)
    expires_at: datetime = Field(sa_type=DateTime(timezone=False), index=True)
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=now_naive, sa_type=DateTime(timezone=False))
