"""Database models for gateway state, retrieval content, and evaluations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


EMBEDDING_DIMENSIONS = 1536


class Base(DeclarativeBase):
    """Base class for ORM models."""


class PromptVersion(Base):
    """Stored prompt template metadata."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("task", "version", name="uq_prompt_versions_task_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(50), index=True)
    template: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Document(Base):
    """Logical source document stored for ingestion and retrieval."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(500), unique=True)
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    """Chunked retrieval unit with optional embedding vector."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")


class QueryLog(Base):
    """Stored request/response records."""

    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task: Mapped[str] = mapped_column(String(100), index=True)
    quality_mode: Mapped[str] = mapped_column(String(50), default="default")
    prompt_version: Mapped[str] = mapped_column(String(50))
    selected_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fallback_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    routing_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[float] = mapped_column(Float)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    evaluation: Mapped["Evaluation | None"] = relationship(
        back_populates="query_log",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Evaluation(Base):
    """Evaluation metrics associated with a gateway response."""

    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint("query_log_id", name="uq_evaluations_query_log_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_log_id: Mapped[int] = mapped_column(ForeignKey("query_logs.id", ondelete="CASCADE"), index=True)
    groundedness_score: Mapped[float] = mapped_column(Float)
    answer_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    citation_score: Mapped[float] = mapped_column(Float, default=0.0)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    query_log: Mapped["QueryLog"] = relationship(back_populates="evaluation")
