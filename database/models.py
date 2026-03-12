"""Database models for prompts, request logs, and evaluations."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for ORM models."""


class PromptVersion(Base):
    """Stored prompt template metadata."""

    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(50), index=True)
    template: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class QueryLog(Base):
    """Stored request/response records."""

    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task: Mapped[str] = mapped_column(String(100), index=True)
    prompt_version: Mapped[str] = mapped_column(String(50))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[float] = mapped_column(Float)
    groundedness_score: Mapped[float] = mapped_column(Float)
    estimated_cost_usd: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
