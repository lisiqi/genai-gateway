"""Streamlit dashboard for request and routing inspection."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from database.models import Evaluation, QueryLog
from database.session import SessionLocal


def load_request_rows() -> tuple[list[dict], str]:
    """Load dashboard rows from Postgres, with JSONL fallback for local resilience."""
    try:
        with SessionLocal() as session:
            rows = (
                session.query(QueryLog, Evaluation)
                .outerjoin(Evaluation, Evaluation.query_log_id == QueryLog.id)
                .order_by(QueryLog.created_at.desc())
                .all()
            )
        table_rows = []
        for query_log, evaluation in rows:
            table_rows.append(
                {
                    "timestamp": query_log.created_at.isoformat() if query_log.created_at else None,
                    "task": query_log.task,
                    "quality_mode": query_log.quality_mode,
                    "provider": query_log.selected_provider,
                    "model": query_log.model_name,
                    "fallback_used": query_log.fallback_used,
                    "fallback_provider": query_log.fallback_provider,
                    "fallback_model": query_log.fallback_model,
                    "routing_reason": query_log.routing_reason,
                    "latency_ms": query_log.latency_ms,
                    "groundedness": evaluation.groundedness_score if evaluation is not None else None,
                    "cost_usd": evaluation.estimated_cost_usd if evaluation is not None else None,
                    "question": query_log.question,
                }
            )
        return table_rows, "Postgres"
    except SQLAlchemyError:
        log_path = Path("logs/requests.jsonl")
        if not log_path.exists():
            return [], "None"
        records = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        table_rows = []
        for record in records:
            request_payload = record.get("request", {})
            response_payload = record.get("response", {})
            routing = response_payload.get("routing", {})
            evaluation = response_payload.get("evaluation", {})
            table_rows.append(
                {
                    "timestamp": record.get("timestamp"),
                    "task": request_payload.get("task"),
                    "quality_mode": request_payload.get("quality_mode") or "default",
                    "provider": routing.get("selected_provider"),
                    "model": routing.get("selected_model"),
                    "fallback_used": routing.get("fallback_used"),
                    "fallback_provider": routing.get("fallback_provider"),
                    "fallback_model": routing.get("fallback_model"),
                    "routing_reason": routing.get("reason"),
                    "latency_ms": response_payload.get("latency_ms"),
                    "groundedness": evaluation.get("groundedness_score"),
                    "cost_usd": evaluation.get("estimated_cost_usd"),
                    "question": request_payload.get("question"),
                }
            )
        return table_rows, "JSONL fallback"


st.set_page_config(page_title="GenAI Gateway Dashboard", layout="wide")
st.title("GenAI Gateway Dashboard")

table_rows, data_source = load_request_rows()
if not table_rows:
    st.info("No request logs found yet. Run the API and send a `/query` request first.")
else:
    fallback_count = 0
    provider_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    for row in table_rows:
        provider = row.get("provider") or "unknown"
        quality_mode = row.get("quality_mode") or "default"
        if row.get("fallback_used"):
            fallback_count += 1
        provider_counts[provider] += 1
        mode_counts[quality_mode] += 1

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Requests logged", len(table_rows))
    col2.metric("Fallback count", fallback_count)
    col3.metric(
        "Fallback rate",
        f"{(fallback_count / len(table_rows) * 100):.1f}%" if table_rows else "0.0%",
    )
    col4.metric("Providers used", len(provider_counts))
    st.caption(f"Data source: {data_source}")

    summary_left, summary_right = st.columns(2)
    with summary_left:
        st.subheader("Provider Distribution")
        st.dataframe(
            pd.DataFrame(
                [{"provider": provider, "requests": count} for provider, count in provider_counts.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )
    with summary_right:
        st.subheader("Quality Mode Distribution")
        st.dataframe(
            pd.DataFrame(
                [{"quality_mode": mode, "requests": count} for mode, count in mode_counts.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Request Log")
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
