"""Streamlit frontend for the legal document Q&A example app."""

from __future__ import annotations

import json
from urllib import error, request

import streamlit as st


DEFAULT_BACKEND_URL = "http://localhost:8010"
PROMPT_OPTIONS = {
    "Grounded answer": {
        "version": "v1",
        "help": "Answers only from retrieved context and says when support is missing.",
    },
    "Research answer with citations": {
        "version": "v2",
        "help": "Pushes for more precise answers, explicit uncertainty, and chunk citations.",
    },
}
QUALITY_MODE_OPTIONS = {
    "Free test": "free",
    "Balanced": "default",
    "Lower cost": "cheap",
    "Higher quality": "high_quality",
}
RERANKER_OPTIONS = {
    "Off": "pass_through",
    "Cross-encoder": "cross_encoder",
}


def chat_backend(
    *,
    backend_url: str,
    session_id: str | None,
    message: str,
    quality_mode: str,
    prompt_version: str,
    top_k: int,
    reranker_type: str,
) -> dict:
    """Call the conversational runtime endpoint over HTTP."""
    payload = json.dumps(
        {
            "session_id": session_id,
            "message": message,
            "quality_mode": quality_mode,
            "prompt_version": prompt_version,
            "retrieval_mode": "hybrid",
            "top_k": top_k,
            "reranker_type": reranker_type,
        }
    ).encode("utf-8")
    req = request.Request(
        url=f"{backend_url.rstrip('/')}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def format_chunk_location(metadata: dict) -> str:
    """Format the main structural location of a retrieved chunk."""
    article_number = metadata.get("article_number")
    clause_numbers = metadata.get("clause_number") or []
    parts: list[str] = []
    if article_number:
        parts.append(f"Article {article_number}")
    if clause_numbers:
        clause_label = ", ".join(str(number) for number in clause_numbers)
        parts.append(f"Clause {clause_label}")
    return " | ".join(parts)


def format_cross_references(metadata: dict) -> list[str]:
    """Format cross-reference metadata for display."""
    references = metadata.get("cross_references") or []
    formatted: list[str] = []
    for reference in references:
        article_number = reference.get("article_number")
        clause_number = reference.get("clause_number")
        scope = reference.get("scope")
        label = f"Article {article_number}"
        if clause_number is not None:
            label += f", Clause {clause_number}"
        if scope == "same_article":
            label += " (same article)"
        formatted.append(label)
    return formatted


def render_qa_result(payload: dict) -> None:
    """Render the standard RAG response payload."""
    result = payload["result"]
    st.subheader("Answer")
    guardrails = result.get("guardrails", {})
    if guardrails.get("abstained"):
        st.warning(
            "Guardrail abstention: "
            + (guardrails.get("reason") or "request blocked before generation")
        )
    st.write(result["answer"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Latency (ms)", f"{result['latency_ms']:.1f}")
    col2.metric("Groundedness", f"{result['evaluation']['groundedness_score']:.2f}")
    col3.metric("Relevance", f"{result['evaluation']['answer_relevance_score']:.2f}")
    col4.metric("Cost (USD)", f"{result['evaluation']['estimated_cost_usd']:.6f}")
    eval_col1, eval_col2 = st.columns(2)
    eval_col1.metric("Citation Score", f"{result['evaluation']['citation_score']:.2f}")
    eval_col2.metric("Completeness", f"{result['evaluation']['completeness_score']:.2f}")
    st.caption(
        "Cost source: "
        f"{result['evaluation'].get('pricing_source') or 'n/a'} | "
        f"input=${result['evaluation']['input_cost_usd']:.6f} | "
        f"output=${result['evaluation']['output_cost_usd']:.6f}"
    )

    route = result["routing"]
    st.caption(
        "Route: "
        f"{route['selected_provider']} / {route['selected_model']} | "
        f"quality_mode={result['quality_mode']} | "
        f"reason={route.get('reason') or 'n/a'}"
    )
    reranking = result["reranking"]
    st.caption(
        "Reranker: "
        f"{reranking['reranker_type']}"
        + (
            f" / {reranking['reranker_model']}"
            if reranking.get("reranker_model")
            else ""
        )
    )
    if guardrails:
        st.caption(
            "Guardrails: "
            f"scope={guardrails.get('scope_status')} | "
            f"evidence={guardrails.get('evidence_status') or 'n/a'} | "
            f"abstained={guardrails.get('abstained')}"
        )
    if route.get("fallback_used"):
        st.warning(
            "Fallback used: "
            f"{route.get('fallback_provider')} / {route.get('fallback_model')}"
        )

    with st.expander("Retrieved Chunks", expanded=True):
        for idx, chunk in enumerate(result["retrieved_chunks"], start=1):
            metadata = chunk.get("metadata", {})
            location = format_chunk_location(metadata)
            title = metadata.get("article_title") or chunk.get("title")
            heading = f"**{idx}. {location or chunk['source']}**"
            if title:
                heading += f"  \n{title}"
            st.markdown(heading)
            if chunk.get("score") is not None:
                caption = f"Similarity score: {chunk['score']:.3f}"
                if chunk.get("rerank_score") is not None:
                    caption += f" | Rerank score: {chunk['rerank_score']:.3f}"
                st.caption(caption)
            elif chunk.get("rerank_score") is not None:
                st.caption(f"Rerank score: {chunk['rerank_score']:.3f}")
            hierarchy_labels = metadata.get("hierarchy_labels") or []
            if hierarchy_labels:
                st.caption("Hierarchy: " + " | ".join(hierarchy_labels))
            st.write(chunk["content"])
            cross_references = format_cross_references(metadata)
            if cross_references:
                st.caption("Cross-references: " + ", ".join(cross_references))
            with st.expander(f"Chunk metadata #{idx}"):
                st.json(metadata)

    with st.expander("Raw Response"):
        st.json(payload)

    with st.expander("Trace"):
        for event in result["trace"]["events"]:
            st.markdown(f"**{event['stage']}**")
            st.caption(f"{event['duration_ms']:.2f} ms")
            if event.get("metadata"):
                st.json(event["metadata"])


def render_agent_result(payload: dict) -> None:
    """Render the controlled agent runtime response."""
    result = payload["result"]
    status = result["status"]
    if status == "completed":
        st.success(f"Run completed: {result['run_id']}")
    elif status == "aborted":
        st.warning(f"Run aborted: {result.get('stop_reason') or 'no stop reason'}")
    else:
        st.info(f"Run status: {status}")

    top1, top2, top3 = st.columns(3)
    top1.metric("Run Status", status)
    top2.metric("Planned Steps", len(result.get("plan", [])))
    top3.metric("Executed Steps", len(result.get("steps", [])))

    with st.expander("Execution Plan", expanded=True):
        for step in result.get("plan", []):
            st.markdown(f"**{step['step_id']} · {step['title']}**")
            st.caption(f"type={step['step_type']} | capability={step['capability_name']}")
            if step.get("inputs"):
                st.json(step["inputs"])

    with st.expander("Step Results", expanded=True):
        for step in result.get("steps", []):
            st.markdown(f"**{step['step_id']} · {step['title']}**")
            st.caption(
                f"status={step['status']} | step_type={step['step_type']} | latency_ms={step.get('latency_ms')}"
            )
            if step.get("checkpoint"):
                checkpoint = step["checkpoint"]
                st.caption(
                    f"checkpoint={checkpoint['decision']} | reason={checkpoint.get('reason') or 'n/a'}"
                )
                if checkpoint.get("metrics"):
                    st.json(checkpoint["metrics"])
            if step.get("output"):
                st.json(step["output"])
            if step.get("error"):
                st.error(step["error"])

    final_output = result.get("final_output", {})
    if final_output:
        st.subheader("Final Output")
        if final_output.get("answer"):
            st.markdown("**Answer**")
            st.write(final_output["answer"])
        email_draft = final_output.get("email_draft") or {}
        if email_draft:
            st.markdown("**Email Draft**")
            st.text_input("Subject", value=email_draft.get("subject", ""), disabled=True)
            st.text_area("Body", value=email_draft.get("body", ""), height=220, disabled=True)

    with st.expander("Raw Response"):
        st.json(payload)


st.set_page_config(page_title="Legal Doc Q&A", layout="wide")
st.title("Legal Document Chat Runtime")
st.caption(
    "Session-aware legal QA chat that routes each turn into standard RAG or the controlled agent runtime."
)

st.sidebar.header("Settings")
prompt_label = st.sidebar.selectbox("Answer style", options=list(PROMPT_OPTIONS), index=0)
st.sidebar.caption(PROMPT_OPTIONS[prompt_label]["help"])
quality_mode_label = st.sidebar.selectbox("Model mode", options=list(QUALITY_MODE_OPTIONS), index=1)
reranker_label = st.sidebar.selectbox("Reranking", options=list(RERANKER_OPTIONS), index=1)
st.sidebar.caption("Cross-encoder usually improves answer quality, but adds latency.")
top_k = st.sidebar.slider("Retrieved chunks", min_value=1, max_value=10, value=4)
if st.sidebar.button("Clear Conversation", use_container_width=True):
    st.session_state.pop("chat_session_id", None)
    st.session_state.pop("chat_messages", None)
    st.session_state.pop("last_chat_payload", None)
with st.sidebar.expander("Advanced", expanded=False):
    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL)

prompt_version = PROMPT_OPTIONS[prompt_label]["version"]
quality_mode = QUALITY_MODE_OPTIONS[quality_mode_label]
reranker_type = RERANKER_OPTIONS[reranker_label]

st.info(
    "Ask legal questions normally, then follow up in the same chat. "
    "If you ask to draft or send an email, the interface routes that turn into the controlled workflow."
)

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = None
if "last_chat_payload" not in st.session_state:
    st.session_state.last_chat_payload = None

for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("caption"):
            st.caption(message["caption"])

user_message = st.chat_input(
    "Ask a legal question or request a workflow like 'draft an email summarizing this answer'."
)
if user_message:
    st.session_state.chat_messages.append({"role": "user", "content": user_message})
    try:
        payload = chat_backend(
            backend_url=backend_url,
            session_id=st.session_state.chat_session_id,
            message=user_message,
            quality_mode=quality_mode,
            prompt_version=prompt_version,
            top_k=top_k,
            reranker_type=reranker_type,
        )
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": f"Backend returned HTTP {exc.code}: {detail}",
                "caption": "request failed",
            }
        )
    except Exception as exc:  # pragma: no cover - UI fallback
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": f"Request failed: {exc}",
                "caption": "request failed",
            }
        )
    else:
        st.session_state.chat_session_id = payload["session_id"]
        caption_parts = [
            f"route={payload['route_kind']}",
            f"effective_question={payload['effective_question']}",
        ]
        if payload.get("recipient_email"):
            caption_parts.append(f"recipient={payload['recipient_email']}")
        if payload.get("routing_reason"):
            caption_parts.append(payload["routing_reason"])
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": payload["assistant_message"],
                "caption": " | ".join(caption_parts),
            }
        )
        st.session_state.last_chat_payload = payload
    st.rerun()

if st.session_state.chat_session_id:
    st.caption(f"Session: {st.session_state.chat_session_id}")

latest_payload = st.session_state.last_chat_payload
if latest_payload:
    st.divider()
    st.subheader("Latest Runtime Details")
    st.caption(
        "The chat interface routes each turn into one execution path and keeps the full structured result for the latest turn."
    )
    if latest_payload["route_kind"] == "qa" and latest_payload.get("qa_result"):
        render_qa_result({"result": latest_payload["qa_result"]})
    elif latest_payload["route_kind"] == "agent" and latest_payload.get("agent_result"):
        render_agent_result({"result": latest_payload["agent_result"]})
