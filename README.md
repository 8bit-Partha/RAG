SecuRAG — Cybersecurity Knowledge Assistant

A Retrieval-Augmented Generation (RAG) chatbot that answers cybersecurity questions using real security policies, NIST 800-53 controls, and OWASP Top 10 data — with every answer grounded in and citing its source, not the model's memory.

Pipeline: heterogeneous document ingestion → structure-aware chunking → BGE embeddings → hybrid (semantic + BM25) retrieval → cross-encoder re-ranking → citation-forced generation with Claude.

Stack: Python · sentence-transformers · ChromaDB · rank-bm25 · Claude API · Streamlit · Docker

Quickstart
bash
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
python -m src.pipeline --build
streamlit run app/streamlit_app.py
License

MIT
