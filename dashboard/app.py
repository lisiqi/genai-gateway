"""Minimal Streamlit dashboard for local request log inspection."""

import json
from pathlib import Path

import streamlit as st


st.set_page_config(page_title="GenAI Gateway Dashboard", layout="wide")
st.title("GenAI Gateway Dashboard")

log_path = Path("logs/requests.jsonl")
if not log_path.exists():
    st.info("No request logs found yet. Run the API and send a `/query` request first.")
else:
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    st.metric("Requests logged", len(records))
    st.dataframe(records, use_container_width=True)
