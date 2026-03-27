"""Streamlit dashboard for experiment and routing inspection."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from database.models import Evaluation, QueryLog
from database.session import SessionLocal


def summarize_trace(trace_json: list[dict]) -> dict[str, object]:
    """Extract dashboard-friendly fields from one request trace."""
    retrieval_ms = sum(
        float(event.get("duration_ms", 0.0))
        for event in trace_json
        if str(event.get("stage", "")).startswith("retrieval.")
    )
    generation_ms = sum(
        float(event.get("duration_ms", 0.0))
        for event in trace_json
        if str(event.get("stage", "")).startswith("generation.")
    )
    retrieval_mode = None
    guardrail_scope_status = None
    guardrail_evidence_status = None
    guardrail_reason = None

    for event in trace_json:
        stage = str(event.get("stage", ""))
        metadata = event.get("metadata") or {}
        if stage == "retrieval.search" and retrieval_mode is None:
            retrieval_mode = metadata.get("retrieval_mode")
        elif stage == "guardrail.scope.result":
            guardrail_scope_status = metadata.get("status")
            guardrail_reason = guardrail_reason or metadata.get("reason")
        elif stage == "guardrail.evidence.result":
            guardrail_evidence_status = metadata.get("status")
            guardrail_reason = guardrail_reason or metadata.get("reason")

    return {
        "retrieval_ms": retrieval_ms,
        "generation_ms": generation_ms,
        "retrieval_mode": retrieval_mode,
        "guardrail_scope_status": guardrail_scope_status,
        "guardrail_evidence_status": guardrail_evidence_status,
        "guardrail_reason": guardrail_reason,
    }


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
            trace_json = query_log.trace_json or []
            trace_summary = summarize_trace(trace_json)
            agent_report = query_log.agent_report_json or {}
            guardrail_abstained = query_log.selected_provider == "guardrail"
            table_rows.append(
                {
                    "timestamp": query_log.created_at.isoformat() if query_log.created_at else None,
                    "request_kind": query_log.request_kind,
                    "task": query_log.task,
                    "quality_mode": query_log.quality_mode,
                    "prompt_version": query_log.prompt_version,
                    "agent_run_id": query_log.agent_run_id,
                    "agent_task_type": query_log.agent_task_type,
                    "instruction": query_log.instruction,
                    "agent_status": query_log.agent_status,
                    "agent_stop_reason": query_log.agent_stop_reason,
                    "agent_step_count": query_log.agent_step_count,
                    "agent_report_json": agent_report,
                    "provider": query_log.selected_provider,
                    "model": query_log.model_name,
                    "reranker_type": query_log.reranker_type,
                    "reranker_model": query_log.reranker_model,
                    "reranker_top_k": query_log.reranker_top_k,
                    "fallback_used": query_log.fallback_used,
                    "fallback_provider": query_log.fallback_provider,
                    "fallback_model": query_log.fallback_model,
                    "routing_reason": query_log.routing_reason,
                    "latency_ms": query_log.latency_ms,
                    "retrieval_ms": trace_summary["retrieval_ms"],
                    "generation_ms": trace_summary["generation_ms"],
                    "retrieval_mode": trace_summary["retrieval_mode"],
                    "guardrail_abstained": guardrail_abstained,
                    "guardrail_scope_status": trace_summary["guardrail_scope_status"],
                    "guardrail_evidence_status": trace_summary["guardrail_evidence_status"],
                    "guardrail_reason": trace_summary["guardrail_reason"] or query_log.routing_reason,
                    "trace_events": len(trace_json),
                    "groundedness": evaluation.groundedness_score if evaluation is not None else None,
                    "answer_relevance": (
                        evaluation.answer_relevance_score if evaluation is not None else None
                    ),
                    "citation_score": evaluation.citation_score if evaluation is not None else None,
                    "completeness_score": (
                        evaluation.completeness_score if evaluation is not None else None
                    ),
                    "cost_usd": evaluation.estimated_cost_usd if evaluation is not None else None,
                    "provider_reported_cost_usd": (
                        evaluation.provider_reported_cost_usd if evaluation is not None else None
                    ),
                    "display_cost_usd": (
                        evaluation.provider_reported_cost_usd
                        if evaluation is not None and evaluation.provider_reported_cost_usd is not None
                        else (evaluation.estimated_cost_usd if evaluation is not None else None)
                    ),
                    "pricing_source": evaluation.pricing_source if evaluation is not None else None,
                    "provider_usage_source": evaluation.provider_usage_source if evaluation is not None else None,
                    "provider_generation_id": evaluation.provider_generation_id if evaluation is not None else None,
                    "cost_is_estimated": evaluation.cost_is_estimated if evaluation is not None else None,
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
            request_kind = record.get("request_kind") or "query"
            request_payload = record.get("request", {})
            response_payload = record.get("response", {})
            if request_kind == "agent_run":
                final_output = response_payload.get("final_output", {})
                answer_metadata = final_output.get("answer_metadata") or {}
                trace_json = []
                for step in response_payload.get("steps", []):
                    step_type = step.get("step_type")
                    output = step.get("output") or {}
                    metadata = {
                        "step_id": step.get("step_id"),
                        "status": step.get("status"),
                    }
                    if step_type == "retrieve_context":
                        stage = "retrieval.search"
                        metadata["retrieval_mode"] = output.get("retrieval_mode")
                    elif step_type == "answer_question":
                        stage = "generation.answer"
                        metadata["provider"] = output.get("provider")
                        metadata["model"] = output.get("model")
                    elif step_type == "draft_email":
                        stage = "generation.draft_email"
                    else:
                        stage = f"agent.{step_type}"
                    trace_json.append(
                        {
                            "stage": stage,
                            "duration_ms": float(step.get("latency_ms") or 0.0),
                            "metadata": metadata,
                        }
                    )
                trace_summary = summarize_trace(trace_json)
                answer_step = next(
                    (
                        step
                        for step in response_payload.get("steps", [])
                        if step.get("step_type") == "answer_question"
                    ),
                    {},
                )
                answer_checkpoint = answer_step.get("checkpoint") or {}
                answer_metrics = answer_checkpoint.get("metrics") or {}
                table_rows.append(
                    {
                        "timestamp": record.get("timestamp"),
                        "request_kind": "agent_run",
                        "task": request_payload.get("task"),
                        "quality_mode": request_payload.get("quality_mode") or "default",
                        "prompt_version": request_payload.get("prompt_version"),
                        "agent_run_id": response_payload.get("run_id"),
                        "agent_task_type": response_payload.get("task_type"),
                        "instruction": request_payload.get("instruction"),
                        "agent_status": response_payload.get("status"),
                        "agent_stop_reason": response_payload.get("stop_reason"),
                        "agent_step_count": len(response_payload.get("steps", [])),
                        "agent_report_json": response_payload,
                        "provider": answer_metadata.get("provider"),
                        "model": answer_metadata.get("model"),
                        "reranker_type": request_payload.get("reranker_type"),
                        "reranker_model": None,
                        "reranker_top_k": None,
                        "fallback_used": answer_metadata.get("fallback_used"),
                        "fallback_provider": None,
                        "fallback_model": None,
                        "routing_reason": response_payload.get("stop_reason"),
                        "latency_ms": sum(float(step.get("latency_ms") or 0.0) for step in response_payload.get("steps", [])),
                        "retrieval_ms": trace_summary["retrieval_ms"],
                        "generation_ms": trace_summary["generation_ms"],
                        "retrieval_mode": trace_summary["retrieval_mode"],
                        "guardrail_abstained": False,
                        "guardrail_scope_status": trace_summary["guardrail_scope_status"],
                        "guardrail_evidence_status": trace_summary["guardrail_evidence_status"],
                        "guardrail_reason": response_payload.get("stop_reason"),
                        "trace_events": len(trace_json),
                        "groundedness": answer_metrics.get("groundedness"),
                        "answer_relevance": answer_metrics.get("answer_relevance"),
                        "citation_score": answer_metrics.get("citation_score"),
                        "completeness_score": answer_metrics.get("completeness"),
                        "cost_usd": answer_step.get("output", {}).get("estimated_cost_usd"),
                        "provider_reported_cost_usd": answer_step.get("output", {}).get("provider_reported_cost_usd"),
                        "display_cost_usd": (
                            answer_step.get("output", {}).get("provider_reported_cost_usd")
                            if answer_step.get("output", {}).get("provider_reported_cost_usd") is not None
                            else answer_step.get("output", {}).get("estimated_cost_usd")
                        ),
                        "pricing_source": answer_step.get("output", {}).get("pricing_source"),
                        "provider_usage_source": answer_step.get("output", {}).get("provider_usage_source"),
                        "provider_generation_id": answer_step.get("output", {}).get("provider_generation_id"),
                        "cost_is_estimated": answer_step.get("output", {}).get("provider_reported_cost_usd") is None,
                        "question": request_payload.get("question"),
                    }
                )
                continue

            routing = response_payload.get("routing", {})
            evaluation = response_payload.get("evaluation", {})
            trace_json = response_payload.get("trace", {}).get("events", [])
            trace_summary = summarize_trace(trace_json)
            guardrails = response_payload.get("guardrails", {})
            table_rows.append(
                {
                    "timestamp": record.get("timestamp"),
                    "request_kind": "query",
                    "task": request_payload.get("task"),
                    "quality_mode": request_payload.get("quality_mode") or "default",
                    "prompt_version": request_payload.get("prompt_version"),
                    "agent_run_id": None,
                    "agent_task_type": None,
                    "instruction": None,
                    "agent_status": None,
                    "agent_stop_reason": None,
                    "agent_step_count": None,
                    "agent_report_json": None,
                    "provider": routing.get("selected_provider"),
                    "model": routing.get("selected_model"),
                    "reranker_type": response_payload.get("reranking", {}).get("reranker_type"),
                    "reranker_model": response_payload.get("reranking", {}).get("reranker_model"),
                    "reranker_top_k": response_payload.get("reranking", {}).get("reranker_top_k"),
                    "fallback_used": routing.get("fallback_used"),
                    "fallback_provider": routing.get("fallback_provider"),
                    "fallback_model": routing.get("fallback_model"),
                    "routing_reason": routing.get("reason"),
                    "latency_ms": response_payload.get("latency_ms"),
                    "retrieval_ms": trace_summary["retrieval_ms"],
                    "generation_ms": trace_summary["generation_ms"],
                    "retrieval_mode": trace_summary["retrieval_mode"],
                    "guardrail_abstained": guardrails.get("abstained", routing.get("selected_provider") == "guardrail"),
                    "guardrail_scope_status": guardrails.get("scope_status") or trace_summary["guardrail_scope_status"],
                    "guardrail_evidence_status": guardrails.get("evidence_status") or trace_summary["guardrail_evidence_status"],
                    "guardrail_reason": guardrails.get("reason") or trace_summary["guardrail_reason"] or routing.get("reason"),
                    "trace_events": len(trace_json),
                    "groundedness": evaluation.get("groundedness_score"),
                    "answer_relevance": evaluation.get("answer_relevance_score"),
                    "citation_score": evaluation.get("citation_score"),
                    "completeness_score": evaluation.get("completeness_score"),
                    "cost_usd": evaluation.get("estimated_cost_usd"),
                    "provider_reported_cost_usd": evaluation.get("provider_reported_cost_usd"),
                    "display_cost_usd": (
                        evaluation.get("provider_reported_cost_usd")
                        if evaluation.get("provider_reported_cost_usd") is not None
                        else evaluation.get("estimated_cost_usd")
                    ),
                    "pricing_source": evaluation.get("pricing_source"),
                    "provider_usage_source": evaluation.get("provider_usage_source"),
                    "provider_generation_id": evaluation.get("provider_generation_id"),
                    "cost_is_estimated": evaluation.get("cost_is_estimated"),
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
    st.sidebar.caption("Leave a selector empty to include all values.")

    request_kind_options = build_filter_options(frame, "request_kind")
    task_options = build_filter_options(frame, "task")
    mode_options = build_filter_options(frame, "quality_mode")
    prompt_options = build_filter_options(frame, "prompt_version")
    provider_options = build_filter_options(frame, "provider")
    model_options = build_filter_options(frame, "model")
    retrieval_mode_options = build_filter_options(frame, "retrieval_mode")
    reranker_type_options = build_filter_options(frame, "reranker_type")
    reranker_model_options = build_filter_options(frame, "reranker_model")
    guardrail_scope_options = build_filter_options(frame, "guardrail_scope_status")

    with st.sidebar.expander("Request Filters", expanded=True):
        selected_request_kinds = st.multiselect(
            "Request Kind",
            options=request_kind_options,
            default=[],
            placeholder="All",
        )
        selected_tasks = st.multiselect("Task", options=task_options, default=[], placeholder="All")
        selected_modes = st.multiselect("Quality Mode", options=mode_options, default=[], placeholder="All")
        selected_prompts = st.multiselect("Prompt Version", options=prompt_options, default=[], placeholder="All")

    with st.sidebar.expander("Runtime Filters", expanded=True):
        selected_providers = st.multiselect("Provider", options=provider_options, default=[], placeholder="All")
        selected_models = st.multiselect("Model", options=model_options, default=[], placeholder="All")
        selected_retrieval_modes = st.multiselect(
            "Retrieval Mode",
            options=retrieval_mode_options,
            default=[],
            placeholder="All",
        )
        selected_reranker_types = st.multiselect(
            "Reranker Type",
            options=reranker_type_options,
            default=[],
            placeholder="All",
        )
        selected_reranker_models = st.multiselect(
            "Reranker Model",
            options=reranker_model_options,
            default=[],
            placeholder="All",
        )

    with st.sidebar.expander("Guardrails", expanded=False):
        selected_guardrail_scopes = st.multiselect(
            "Guardrail Scope",
            options=guardrail_scope_options,
            default=[],
            placeholder="All",
        )
        fallback_only = st.checkbox("Fallback Only", value=False)
        abstentions_only = st.checkbox("Guardrail Abstentions Only", value=False)

    filtered = frame.copy()
    if selected_request_kinds:
        filtered = filtered[filtered["request_kind"].isin(selected_request_kinds)]
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
    if selected_retrieval_modes:
        filtered = filtered[filtered["retrieval_mode"].isin(selected_retrieval_modes)]
    if selected_reranker_types:
        filtered = filtered[filtered["reranker_type"].isin(selected_reranker_types)]
    if selected_reranker_models:
        filtered = filtered[filtered["reranker_model"].isin(selected_reranker_models)]
    if selected_guardrail_scopes:
        filtered = filtered[filtered["guardrail_scope_status"].isin(selected_guardrail_scopes)]
    if fallback_only:
        filtered = filtered[filtered["fallback_used"] == True]
    if abstentions_only:
        filtered = filtered[filtered["guardrail_abstained"] == True]
    return filtered


def render_summary_metrics(frame: pd.DataFrame, data_source: str) -> None:
    """Render top-line comparison metrics."""
    fallback_rate = (frame["fallback_used"].fillna(False).mean() * 100) if not frame.empty else 0.0
    avg_latency = frame["latency_ms"].mean() if not frame.empty else 0.0
    avg_retrieval = frame["retrieval_ms"].mean() if not frame.empty else 0.0
    avg_generation = frame["generation_ms"].mean() if not frame.empty else 0.0
    avg_groundedness = frame["groundedness"].mean() if not frame.empty else 0.0
    avg_relevance = frame["answer_relevance"].mean() if not frame.empty else 0.0
    avg_cost = frame["display_cost_usd"].mean() if not frame.empty else 0.0
    abstention_rate = (frame["guardrail_abstained"].fillna(False).mean() * 100) if not frame.empty else 0.0

    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    col1.metric("Requests", len(frame))
    col2.metric("Avg Latency (ms)", f"{avg_latency:.1f}")
    col3.metric("Avg Retrieval (ms)", f"{avg_retrieval:.1f}")
    col4.metric("Avg Generation (ms)", f"{avg_generation:.1f}")
    col5.metric("Avg Groundedness", f"{avg_groundedness:.2f}")
    col6.metric("Avg Relevance", f"{avg_relevance:.2f}")
    col7.metric("Fallback Rate", f"{fallback_rate:.1f}%")
    col8.metric("Abstention Rate", f"{abstention_rate:.1f}%")
    st.metric("Avg Cost (USD)", f"{avg_cost:.6f}")
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
            avg_retrieval_ms=("retrieval_ms", "mean"),
            avg_generation_ms=("generation_ms", "mean"),
            avg_groundedness=("groundedness", "mean"),
            avg_relevance=("answer_relevance", "mean"),
            avg_citation=("citation_score", "mean"),
            avg_completeness=("completeness_score", "mean"),
            avg_cost_usd=("display_cost_usd", "mean"),
            fallback_rate=("fallback_used", "mean"),
            abstention_rate=("guardrail_abstained", "mean"),
        )
        .reset_index()
    )
    grouped["fallback_rate"] = grouped["fallback_rate"].fillna(0.0) * 100
    grouped["abstention_rate"] = grouped["abstention_rate"].fillna(0.0) * 100
    return grouped.round(
        {
            "avg_latency_ms": 1,
            "avg_retrieval_ms": 1,
            "avg_generation_ms": 1,
            "avg_groundedness": 2,
            "avg_relevance": 2,
            "avg_citation": 2,
            "avg_completeness": 2,
            "avg_cost_usd": 6,
            "fallback_rate": 1,
            "abstention_rate": 1,
        }
    )


def render_group_tables(frame: pd.DataFrame) -> None:
    """Render grouped comparison tables."""
    sections = [
        ("By Request Kind", "request_kind"),
        ("By Quality Mode", "quality_mode"),
        ("By Retrieval Mode", "retrieval_mode"),
        ("By Model", "model"),
        ("By Reranker", "reranker_type"),
        ("By Guardrail Scope", "guardrail_scope_status"),
        ("By Agent Status", "agent_status"),
    ]
    for title, group_by in sections:
        st.subheader(title)
        st.dataframe(build_group_summary(frame, group_by), use_container_width=True, hide_index=True)


def render_request_log(frame: pd.DataFrame) -> None:
    """Render request-level drilldown."""
    display_columns = [
        "timestamp",
        "request_kind",
        "task",
        "quality_mode",
        "prompt_version",
        "agent_run_id",
        "agent_task_type",
        "agent_status",
        "agent_stop_reason",
        "agent_step_count",
        "provider",
        "model",
        "retrieval_mode",
        "reranker_type",
        "reranker_model",
        "reranker_top_k",
        "guardrail_abstained",
        "guardrail_scope_status",
        "guardrail_evidence_status",
        "guardrail_reason",
        "fallback_used",
        "fallback_provider",
        "fallback_model",
        "routing_reason",
        "latency_ms",
        "retrieval_ms",
        "generation_ms",
        "trace_events",
        "groundedness",
        "answer_relevance",
        "citation_score",
        "completeness_score",
        "cost_usd",
        "provider_reported_cost_usd",
        "provider_usage_source",
        "provider_generation_id",
        "pricing_source",
        "cost_is_estimated",
        "instruction",
        "question",
    ]
    st.subheader("Run Log")
    st.dataframe(frame[display_columns], use_container_width=True, hide_index=True)

    agent_rows = frame[frame["request_kind"] == "agent_run"]
    if not agent_rows.empty:
        st.subheader("Agent Run Reports")
        options = [
            f"{row.agent_run_id} | {row.agent_status} | {row.question}"
            for row in agent_rows[["agent_run_id", "agent_status", "question"]].itertuples(index=False)
        ]
        selected = st.selectbox("Inspect Agent Run", options=options)
        selected_run_id = selected.split(" | ", 1)[0]
        selected_row = agent_rows[agent_rows["agent_run_id"] == selected_run_id].iloc[0]
        st.json(selected_row["agent_report_json"])


st.set_page_config(page_title="GenAI Gateway Dashboard", layout="wide")
st.title("GenAI Gateway Dashboard")

table_rows, data_source = load_request_rows()
if not table_rows:
    st.info("No runtime logs found yet. Run the API and send a `/ask` or `/agent/run` request first.")
else:
    full_frame = pd.DataFrame(table_rows)
    filtered_frame = apply_filters(full_frame)
    if filtered_frame.empty:
        st.warning("No rows match the current filters.")
    else:
        render_summary_metrics(filtered_frame, data_source=data_source)
        render_group_tables(filtered_frame)
        render_request_log(filtered_frame)
