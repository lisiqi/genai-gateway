"""Streamlit frontend for the legal document Q&A example app."""

from __future__ import annotations

import json
from urllib import error, request

import streamlit as st


DEFAULT_BACKEND_URL = "http://localhost:8010"


def ask_backend(*, backend_url: str, question: str, prompt_version: str, top_k: int) -> dict:
    """Call the example app backend over HTTP."""
    payload = json.dumps(
        {
            "question": question,
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


st.set_page_config(page_title="Legal Doc Q&A", layout="wide")
st.title("Legal Document Q&A")
st.caption("Example application built on top of the genai_gateway runtime.")

backend_url = st.sidebar.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
prompt_version = st.sidebar.selectbox("Prompt version", options=["v1", "v2"], index=0)
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

            col1, col2, col3 = st.columns(3)
            col1.metric("Latency (ms)", f"{result['latency_ms']:.1f}")
            col2.metric("Groundedness", f"{result['evaluation']['groundedness_score']:.2f}")
            col3.metric("Cost (USD)", f"{result['evaluation']['estimated_cost_usd']:.6f}")

            with st.expander("Retrieved Chunks", expanded=True):
                for idx, chunk in enumerate(result["retrieved_chunks"], start=1):
                    st.markdown(f"**{idx}. {chunk['source']}**")
                    st.write(chunk["content"])

            with st.expander("Raw Response"):
                st.json(payload)
