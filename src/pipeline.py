"""
End-to-end SecuRAG pipeline.

Two entry points:
  - build_index()  : ingest -> chunk -> embed -> store   (run once, or
                      whenever source documents change)
  - answer(query)   : retrieve -> rerank -> generate      (run per query)

Kept in one file so the full flow is easy to read top to bottom; the
actual logic for each stage lives in its own module under src/.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.document_loader import load_directory
from src.chunking.chunker import chunk_records
from src.embeddings.embedder import Embedder
from src.vectorstore.chroma_store import VectorStore
from src.retrieval.hybrid_search import HybridRetriever
from src.retrieval.reranker import Reranker
from src.generation.answer_generator import AnswerGenerator

RAW_DIR = "data/raw"
CHUNKS_PATH = "data/processed/chunks.json"
CONTEXTUAL_CHUNKS_PATH = "data/processed/chunks_contextual.json"


def build_index(use_contextual: bool = False):
    """
    Run once to (re)build the searchable index from data/raw.

    use_contextual: if True, runs the contextual retrieval enrichment
    step (src/chunking/contextual_enrichment.py) before embedding, which
    calls the Claude API once per chunk to prepend document-level context.
    This costs a small amount of API usage proportional to corpus size
    and requires ANTHROPIC_API_KEY to be set. It's optional because the
    baseline pipeline (structure-aware chunking with context headers) is
    already reasonable for small, well-organized corpora -- contextual
    retrieval earns its cost most on larger or less-structured corpora.
    """
    print("1/3 Loading and parsing documents...")
    records = load_directory(RAW_DIR)

    print("2/3 Chunking...")
    chunks = chunk_records(records)
    with open(CHUNKS_PATH, "w") as f:
        json.dump(chunks, f, indent=2)
    print(f"   {len(records)} records -> {len(chunks)} chunks")

    if use_contextual:
        print("2b/3 Running contextual enrichment (API calls, one per chunk)...")
        from src.chunking.contextual_enrichment import ContextualEnricher
        enricher = ContextualEnricher()
        chunks = enricher.enrich_all(chunks)
        with open(CONTEXTUAL_CHUNKS_PATH, "w") as f:
            json.dump(chunks, f, indent=2)
        embed_field = "contextualized_text"
    else:
        embed_field = "raw_text"

    print("3/3 Embedding and indexing...")
    embedder = Embedder()
    vectors = embedder.embed_documents([c[embed_field] for c in chunks])

    store = VectorStore()
    store.add_chunks(chunks, vectors)
    print(f"   Indexed {store.count()} chunks into the vector store.")
    print("\nIndex build complete. Run pipeline.answer(query) to query it.")


class SecuRAGPipeline:
    """Loaded once (e.g. at app startup); reused across many queries."""

    def __init__(self):
        # Prefer contextually-enriched chunks if they were built; falls
        # back to plain chunks otherwise (see build_index).
        chunks_path = CONTEXTUAL_CHUNKS_PATH if Path(CONTEXTUAL_CHUNKS_PATH).exists() else CHUNKS_PATH
        with open(chunks_path) as f:
            self.chunks = json.load(f)

        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.retriever = HybridRetriever(self.chunks, self.vector_store, self.embedder)
        self.reranker = Reranker()
        self.generator = AnswerGenerator()

    def answer(self, query: str, candidate_pool: int = 15, final_k: int = 5) -> dict:
        candidates = self.retriever.search(query, top_k=candidate_pool)
        top_chunks = self.reranker.rerank(query, candidates, top_k=final_k)
        result = self.generator.generate(query, top_chunks)
        result["retrieved_chunks"] = top_chunks
        return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Build the index from data/raw")
    parser.add_argument("--contextual", action="store_true",
                         help="With --build: also run contextual retrieval enrichment (extra API calls)")
    parser.add_argument("--query", type=str, help="Ask a question against the built index")
    args = parser.parse_args()

    if args.build:
        build_index(use_contextual=args.contextual)
    elif args.query:
        pipeline = SecuRAGPipeline()
        result = pipeline.answer(args.query)
        print("\nANSWER:\n", result["answer"])
        print("\nSOURCES:")
        for s in result["sources"]:
            print(f"  - {s['source']} / {s['section']}")
    else:
        parser.print_help()
