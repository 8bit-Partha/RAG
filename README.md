# RAG-Ai — Cybersecurity Knowledge Assistant

A Retrieval-Augmented Generation (RAG) chatbot that answers cybersecurity
questions grounded in real source documents — security policies, and
structured threat-intelligence data — with citations, so answers can
always be traced back to the original text instead of trusted blindly.

Built as a hands-on project to learn the full RAG pipeline end to end:
parsing heterogeneous documents, structure-aware chunking, embeddings,
vector search, hybrid retrieval, re-ranking, citation-grounded
generation, and quantitative evaluation.

## Why this exists

Most RAG tutorials stop at "embed some text, do a vector search." This
project goes further on purpose, because those extra pieces are where
real-world RAG quality actually comes from:

- **Heterogeneous ingestion** — handles both unstructured policy
  documents (Markdown/PDF) and structured threat-intel records (JSON) in
  one pipeline.
- **Structure-aware chunking** — splits along document sections rather
  than arbitrary character counts, and attaches a source/section header
  to every chunk so meaning isn't lost in isolation.
- **Hybrid retrieval** — combines semantic (vector) search with BM25
  keyword search via Reciprocal Rank Fusion, because security queries mix
  natural language ("how do we handle a breach") with exact identifiers
  ("AC-2", "TA0006", CVE numbers) that pure semantic search can miss.
- **Cross-encoder re-ranking** — a second, more precise pass over the
  initial candidates before anything reaches the LLM.
- **Citation-forced generation** — the model is instructed to cite
  `[source: section]` for every claim and to say "I don't know" rather
  than guess, which matters a lot when wrong answers in a
  compliance-adjacent domain carry real risk.
- **Separate retrieval/generation evaluation** — so when the system gets
  something wrong, you can tell whether retrieval failed to find the
  right passage, or generation ignored a passage it was given.

## Architecture

```
data/raw/ (Markdown policies, PDFs, JSON threat data)
        │
        ▼
 ingestion/document_loader.py   — parses each format into a common
        │                          {text, source, section, doc_type} shape
        ▼
 chunking/chunker.py            — structure-aware splitting, adds
        │                          context headers + stable chunk_ids
        ▼
 embeddings/embedder.py         — BAAI/bge-small-en-v1.5 (local, offline)
        │
        ▼
 vectorstore/chroma_store.py    — persisted Chroma collection
        │
        ▼
 ┌──────────────────────────────────────────┐
 │  retrieval/hybrid_search.py               │
 │    semantic search  ─┐                    │
 │                       ├─ RRF fusion        │
 │    BM25 keyword     ─┘                    │
 └──────────────────────────────────────────┘
        │
        ▼
 retrieval/reranker.py          — cross-encoder re-ranks top candidates
        │
        ▼
 generation/answer_generator.py — Claude API, citation-forced prompt
        │
        ▼
 app/streamlit_app.py           — chat UI, shows answer + sources
```

`src/pipeline.py` wires all of the above into two entry points:
`build_index()` (run once per corpus) and `SecuRAGPipeline.answer(query)`
(run per question).

## Project structure

```
securag/
├── data/
│   ├── raw/            # source documents (sample policies + threat data included)
│   └── processed/      # generated: chunks.json, chroma_db/
├── src/
│   ├── ingestion/       document_loader.py
│   ├── chunking/        chunker.py
│   ├── embeddings/      embedder.py
│   ├── vectorstore/     chroma_store.py
│   ├── retrieval/       hybrid_search.py, reranker.py
│   ├── generation/      answer_generator.py
│   └── pipeline.py
├── eval/
│   ├── test_questions.json   # 10 labeled Q&A pairs
│   └── evaluate.py
├── app/
│   └── streamlit_app.py
└── requirements.txt
```

## Data included

The repo ships with a real, heterogeneous corpus — not just toy data —
so the pipeline demonstrates handling multiple source types at once:

| File | Type | Content |
|---|---|---|
| `incident_response_policy.md` | Markdown policy | Original sample policy document |
| `access_control_policy.md` | Markdown policy | Original sample policy document |
| `acceptable_use_policy.md` | Markdown policy | Original sample policy document |
| `threat_tactics.json` | Structured | MITRE ATT&CK-style adversary tactic categories (TA0001–TA0010) |
| `nist_800_53_families.json` | Structured | All 20 real NIST SP 800-53 Rev 5 control families, with original descriptions |
| `owasp_top10_2021.json` | Structured | The real OWASP Top 10:2021 categories, with original descriptions |

The policy documents are original content, written for this project, so
there's no copyright concern reproducing them. The NIST and OWASP files
use the real, factual taxonomy (control family names/IDs, category
names — not copyrightable expression) paired with original explanatory
text rather than text copied from the source publications.

**To go further**, drop real primary-source documents into `data/raw/`:
- Full NIST SP 800-53 / 800-171 text (PDF) — nist.gov
- OWASP Cheat Sheets (Markdown/PDF) — owasp.org
- MITRE ATT&CK full technique catalog (JSON via their STIX feed) — attack.mitre.org
- Your own organization's policies

Then re-run `python -m src.pipeline --build`. If you add a new
structured JSON source with different field names, register it in
`STRUCTURED_FIELD_MAP` in `src/ingestion/document_loader.py`.

## Features beyond the baseline pipeline

- **Contextual retrieval** (`src/chunking/contextual_enrichment.py`) —
  implements Anthropic's [Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
  technique: before embedding, an LLM call generates a short
  document-level context for each chunk and prepends it, so a chunk's
  embedding reflects its place in the full document, not just its own
  text in isolation. Optional — enable with `--build --contextual`
  (costs one API call per chunk).
- **Unit tests** (`tests/`) — real tests for chunking behavior, document
  loading, and hybrid search/RRF fusion logic, runnable without an API
  key or heavy ML dependencies.
- **CI** (`.github/workflows/ci.yml`) — runs the test suite and a
  compile check on every push, using only lightweight dependencies so it
  stays fast and free to run.
- **Docker / docker-compose** — containerized deployment that builds the
  index at image build time and serves the Streamlit UI.

## Tech stack

Python · sentence-transformers (BGE embeddings) · ChromaDB · rank-bm25 ·
Claude API (Anthropic, including for contextual retrieval enrichment) ·
Streamlit · Docker · pytest · GitHub Actions.
The CI workflow (`.github/workflows/ci.yml`) runs automatically on every
push once the repo is on GitHub — no setup neede
