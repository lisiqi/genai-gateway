"""Streamlit dashboard for experiment and routing inspection."""

from __future__ import annotations

import json
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
                    "prompt_version": query_log.prompt_version,
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
                    "prompt_version": request_payload.get("prompt_version"),
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


def build_filter_options(frame: pd.DataFrame, column: str) -> list[str]:
    """Return sorted unique filter options for a column."""
    values = [value for value in frame[column].dropna().unique().tolist() if value != ""]
    return sorted(values)


def apply_filters(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply sidebar filters to the dashboard dataset."""
    st.sidebar.header("Filters")

    task_options = build_filter_options(frame, "task")
    mode_options = build_filter_options(frame, "quality_mode")
    prompt_options = build_filter_options(frame, "prompt_version")
    provider_options = build_filter_options(frame, "provider")
    model_options = build_filter_options(frame, "model")

    selected_tasks = st.sidebar.multiselect("Task", options=task_options, default=task_options)
    selected_modes = st.sidebar.multiselect("Quality Mode", options=mode_options, default=mode_options)
    selected_prompts = st.sidebar.multiselect("Prompt Version", options=prompt_options, default=prompt_options)
    selected_providers = st.sidebar.multiselect("Provider", options=provider_options, default=provider_options)
    selected_models = st.sidebar.multiselect("Model", options=model_options, default=model_options)
    fallback_only = st.sidebar.checkbox("Fallback Only", value=False)

    filtered = frame.copy()
    if selected_tasks:
        filtered = filtered[filtered["task"].isin(selected_tasks)]
    if selected_modes:
        filtered = filtered[filtered["quality_mode"].isin(selected_modes)]
    if selected_prompts:
        filtered = filtered[filtered["prompt_version"].isin(selected_prompts)]
    if selected_providers:
        filtered = filtered[filtered["provider"].isin(selected_providers)]
    if selected_models:
        filtered = filtered[filtered["model"].isin(selected_models)]
    if fallback_only:
        filtered = filtered[filtered["fallback_used"] == True]
    return filtered


def render_summary_metrics(frame: pd.DataFrame, data_source: str) -> None:
    """Render top-line comparison metrics."""
    fallback_rate = (frame["fallback_used"].fillna(False).mean() * 100) if not frame.empty else 0.0
    avg_latency = frame["latency_ms"].mean() if not frame.empty else 0.0
    avg_groundedness = frame["groundedness"].mean() if not frame.empty else 0.0
    avg_cost = frame["cost_usd"].mean() if not frame.empty else 0.0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Requests", len(frame))
    col2.metric("Avg Latency (ms)", f"{avg_latency:.1f}")
    col3.metric("Avg Groundedness", f"{avg_groundedness:.2f}")
    col4.metric("Avg Cost (USD)", f"{avg_cost:.6f}")
    col5.metric("Fallback Rate", f"{fallback_rate:.1f}%")
    st.caption(f"Data source: {data_source}")


def build_group_summary(frame: pd.DataFrame, group_by: str) -> pd.DataFrame:
    """Build grouped comparison metrics for one dimension."""
    if frame.empty:
        return pd.DataFrame()
    grouped = (
        frame.groupby(group_by, dropna=False)
        .agg(
            requests=("question", "count"),
            avg_latency_ms=("latency_ms", "mean"),
            avg_groundedness=("groundedness", "mean"),
            avg_cost_usd=("cost_usd", "mean"),
            fallback_rate=("fallback_used", "mean"),
        )
        .reset_index()
    )
    grouped["fallback_rate"] = grouped["fallback_rate"].fillna(0.0) * 100
    return grouped.round(
        {
            "avg_latency_ms": 1,
            "avg_groundedness": 2,
            "avg_cost_usd": 6,
            "fallback_rate": 1,
        }
    )


def render_group_tables(frame: pd.DataFrame) -> None:
    """Render grouped comparison tables."""
    left, middle, right = st.columns(3)
    with left:
        st.subheader("By Quality Mode")
        st.dataframe(build_group_summary(frame, "quality_mode"), use_container_width=True, hide_index=True)
    with middle:
        st.subheader("By Prompt Version")
        st.dataframe(build_group_summary(frame, "prompt_version"), use_container_width=True, hide_index=True)
    with right:
        st.subheader("By Model")
        st.dataframe(build_group_summary(frame, "model"), use_container_width=True, hide_index=True)


def render_request_log(frame: pd.DataFrame) -> None:
    """Render request-level drilldown."""
    display_columns = [
        "timestamp",
        "task",
        "quality_mode",
        "prompt_version",
        "provider",
        "model",
        "fallback_used",
        "fallback_provider",
        "fallback_model",
        "routing_reason",
        "latency_ms",
        "groundedness",
        "cost_usd",
        "question",
    ]
    st.subheader("Request Log")
    st.dataframe(frame[display_columns], use_container_width=True, hide_index=True)


st.set_page_config(page_title="GenAI Gateway Dashboard", layout="wide")
st.title("GenAI Gateway Dashboard")

table_rows, data_source = load_request_rows()
if not table_rows:
    st.info("No request logs found yet. Run the API and send a `/query` request first.")
else:
    full_frame = pd.DataFrame(table_rows)
    filtered_frame = apply_filters(full_frame)
    if filtered_frame.empty:
        st.warning("No rows match the current filters.")
    else:
        render_summary_metrics(filtered_frame, data_source=data_source)
        render_group_tables(filtered_frame)
        render_request_log(filtered_frame)
