"""
SecuRAG chat UI.

Run locally with:  streamlit run app/streamlit_app.py

Deployment-ready: if no index has been built yet (fresh clone, or a fresh
deploy on Streamlit Community Cloud), this builds one automatically on
first load instead of crashing or requiring a manual `--build` step.
Missing API keys and pipeline errors are shown as in-app messages rather
than uncaught exceptions, since a stack trace is a poor first impression
for anyone opening a deployed link.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(page_title="SecuRAG", page_icon="🛡️", layout="centered")
st.title("🛡️ SecuRAG — Cybersecurity Knowledge Assistant")
st.caption("Answers are grounded in policy documents and threat-intel data, with citations.")

# ---- API key check, before anything expensive happens ----
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(
        "**ANTHROPIC_API_KEY is not set.**\n\n"
        "Locally: copy `.env.example` to `.env` and add your key.\n\n"
        "On Streamlit Community Cloud: add it under *App settings → Secrets* as "
        "`ANTHROPIC_API_KEY = \"sk-ant-...\"`.",
        icon="🔑",
    )
    st.stop()

from src.pipeline import SecuRAGPipeline, CHUNKS_PATH, build_index


@st.cache_resource(show_spinner=False)
def load_pipeline():
    # Fresh clone / fresh deploy: no index built yet. Build one now so the
    # app is usable without a manual setup step. This costs real time on
    # first load only (embedding the sample corpus takes well under a
    # minute); subsequent loads reuse the persisted Chroma collection.
    if not Path(CHUNKS_PATH).exists():
        with st.spinner("First-time setup: building the search index from data/raw... this takes a minute."):
            build_index()
    return SecuRAGPipeline()


try:
    pipeline = load_pipeline()
except Exception as e:
    st.error(f"Couldn't initialize the pipeline: {e}")
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.subheader("About")
    st.markdown(
        "Answers are retrieved from the documents in `data/raw/` — sample "
        "security policies plus NIST 800-53 and OWASP Top 10 taxonomy — "
        "then generated with citations. Nothing is answered from the "
        "model's general knowledge alone."
    )
    st.markdown(f"**Indexed chunks:** {len(pipeline.chunks)}")

for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])
        if turn["role"] == "assistant" and turn.get("sources"):
            with st.expander("Sources"):
                for s in turn["sources"]:
                    st.markdown(f"- **{s['source']}** / {s['section']}")

if query := st.chat_input("Ask about incident response, access control, NIST controls, OWASP risks..."):
    st.session_state.history.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving and generating..."):
            try:
                result = pipeline.answer(query)
            except Exception as e:
                st.error(f"Something went wrong answering that: {e}")
                st.stop()
        st.markdown(result["answer"])
        with st.expander("Sources"):
            for s in result["sources"]:
                st.markdown(f"- **{s['source']}** / {s['section']}")

    st.session_state.history.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
    })
