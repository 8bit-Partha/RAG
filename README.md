# SecuRAG — Cybersecurity Knowledge Assistant

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

## Setup

```bash
git clone <your-repo-url>
cd securag
python -m venv .venv && source .venv/bin/activate     # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env      # then add your ANTHROPIC_API_KEY
```

## Usage

**1. Build the index** (parses `data/raw/`, chunks, embeds, stores in Chroma):

```bash
python -m src.pipeline --build

# Or, to also run contextual retrieval enrichment (extra API calls, better
# retrieval quality on longer/less-structured documents):
python -m src.pipeline --build --contextual
```

**2. Ask a question from the command line:**

```bash
python -m src.pipeline --query "How long does temporary elevated access last?"
```

**3. Or launch the chat UI:**

```bash
streamlit run app/streamlit_app.py
```

**4. Run the evaluation suite:**

```bash
python -m eval.evaluate                # retrieval + generation (needs API key)
python -m eval.evaluate --no-generation  # retrieval only, no API key needed
```

This prints retrieval hit rate and generation groundedness against the
20 labeled questions in `eval/test_questions.json`, and writes per-question
detail to `eval/results.json`. Run it after you build the index to get
real numbers for your own copy of the project.

**5. Run the unit tests:**

```bash
pytest tests/ -v
```

**6. Or run everything in Docker:**

```bash
cp .env.example .env   # add your API key
docker compose up --build
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

## Design notes / things I'd improve next

- Swap Chroma for Qdrant if scaling past a single-machine demo —
  interface in `chroma_store.py` maps directly.
- Add metadata filtering in the UI (e.g. "search only NIST controls")
  using the `doc_type` field already attached to every chunk.
- Replace the evaluation script's simple citation-match check with
  [Ragas](https://docs.ragas.io) for LLM-graded faithfulness and context
  precision metrics.
- Add reciprocal rank fusion weight tuning — currently both search
  methods are weighted equally; a labeled eval set (already included)
  makes it possible to tune this empirically instead of guessing.

## Tech stack

Python · sentence-transformers (BGE embeddings) · ChromaDB · rank-bm25 ·
Claude API (Anthropic, including for contextual retrieval enrichment) ·
Streamlit · Docker · pytest · GitHub Actions

## Deployment

Two supported paths, depending on where you want it running.

### Option A — Streamlit Community Cloud (free, easiest)

1. Push this repo to GitHub (see below).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in, and pick
   **New app** → select your repo → set the main file path to
   `app/streamlit_app.py`.
3. Under **Advanced settings → Secrets**, add:
   ```
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ```
4. Deploy. The app builds its search index automatically on first load
   (see `app/streamlit_app.py`) — no manual `--build` step needed for a
   fresh deploy.

**Resource note:** the free tier has limited memory, and
`sentence-transformers` + `chromadb` are not lightweight. If the app
struggles to start on the free tier, that's a resource-limit issue, not
a code issue — Option B gives you more headroom.

### Option B — Docker (Render, Railway, Fly.io, or any VPS)

The included `Dockerfile` builds the index at image build time, so the
container is ready to serve immediately:

```bash
docker compose up --build
```

For a hosting provider (Render, Railway, Fly.io all support this
pattern): point it at this repo, let it build from the `Dockerfile`, and
set `ANTHROPIC_API_KEY` as an environment variable/secret in the
provider's dashboard. Expose port `8501`.

## Publishing to GitHub

```bash
git init                      # skip if already a git repo
git add .
git commit -m "Initial commit: SecuRAG RAG pipeline"
git branch -M main
git remote add origin https://github.com/<your-username>/securag.git
git push -u origin main
```

`.gitignore` already excludes `.env`, the built index
(`data/processed/chroma_db/`, `chunks.json`), and Python cache files —
so secrets and generated artifacts won't end up in the repo. Double
check `git status` before your first commit if you've been running the
pipeline locally, since a build will have created those files.

The CI workflow (`.github/workflows/ci.yml`) runs automatically on every
push once the repo is on GitHub — no setup needed, it uses only
lightweight dependencies so it doesn't require secrets to run.
