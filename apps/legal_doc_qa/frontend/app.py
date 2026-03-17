"""Streamlit frontend for the legal document Q&A example app."""

from __future__ import annotations

import json
from urllib import error, request

import streamlit as st


DEFAULT_BACKEND_URL = "http://localhost:8010"


def ask_backend(*, backend_url: str, question: str, quality_mode: str, prompt_version: str, top_k: int) -> dict:
    """Call the example app backend over HTTP."""
    payload = json.dumps(
        {
            "question": question,
            "quality_mode": quality_mode,
            "prompt_version": prompt_version,
            "top_k": top_k,
        }
    ).encode("utf-8")
    req = request.Request(
        url=f"{backend_url.rstrip('/')}/ask",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=60) as response:
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


st.set_page_config(page_title="Legal Doc Q&A", layout="wide")
st.title("Legal Document Q&A")
st.caption("Example application built on top of the genai_gateway runtime.")

backend_url = st.sidebar.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
prompt_version = st.sidebar.selectbox("Prompt version", options=["v1", "v2"], index=0)
quality_mode = st.sidebar.selectbox("Quality mode", options=["cheap", "default", "high_quality"], index=1)
top_k = st.sidebar.slider("Top K", min_value=1, max_value=10, value=4)

question = st.text_area(
    "Question",
    value="What is the aim of this Regulation?",
    height=120,
)

if st.button("Ask", type="primary", use_container_width=True):
    if not question.strip():
        st.error("Question is required.")
    else:
        try:
            payload = ask_backend(
                backend_url=backend_url,
                question=question.strip(),
                quality_mode=quality_mode,
                prompt_version=prompt_version,
                top_k=top_k,
            )
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            st.error(f"Backend returned HTTP {exc.code}: {detail}")
        except Exception as exc:  # pragma: no cover - UI fallback
            st.error(f"Request failed: {exc}")
        else:
            result = payload["result"]
            st.subheader("Answer")
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
