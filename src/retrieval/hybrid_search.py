"""
Hybrid retrieval for SecuRAG: combines semantic (vector) search with BM25
keyword search.

Why hybrid, specifically for cybersecurity docs:
  - Semantic search is good at intent ("how do we handle a breach?" ->
    finds "Incident Response Procedure" even with zero shared words).
  - Keyword search (BM25) is good at exact tokens: control IDs like
    "AC-2", CVE numbers, acronyms like "MFA" -- cases where you want an
    exact match, not a "similar meaning" match, and where a semantic
    model might not weight a rare exact code highly enough.

Results from both methods are merged using Reciprocal Rank Fusion (RRF),
a simple, parameter-light way to combine ranked lists without needing to
tune how to weight each method's raw scores against each other.
"""

from typing import List, Dict
from rank_bm25 import BM25Okapi
import re


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class HybridRetriever:
    def __init__(self, chunks: List[Dict], vector_store, embedder):
        """
        chunks: full chunk list (from chunker.py) -- used to build the
                BM25 index.
        vector_store: a VectorStore instance already populated with these
                      same chunks' embeddings.
        embedder: an Embedder instance, for embedding the query.
        """
        self.chunks = chunks
        self.chunk_by_id = {c["chunk_id"]: c for c in chunks}
        self.vector_store = vector_store
        self.embedder = embedder

        tokenized_corpus = [_tokenize(c["raw_text"]) for c in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def _bm25_search(self, query: str, top_k: int) -> List[str]:
        scores = self.bm25.get_scores(_tokenize(query))
        ranked_idx = sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
        return [self.chunks[i]["chunk_id"] for i in ranked_idx]

    def _semantic_search(self, query: str, top_k: int) -> List[str]:
        query_vec = self.embedder.embed_query(query)
        hits = self.vector_store.query(query_vec, top_k=top_k)
        return [h["chunk_id"] for h in hits]

    def search(self, query: str, top_k: int = 10, candidate_pool: int = 20, rrf_k: int = 60) -> List[Dict]:
        """
        Run both search methods, merge with Reciprocal Rank Fusion:

            score(doc) = sum over each ranked list of  1 / (rrf_k + rank)

        A document that ranks highly in EITHER list gets a meaningful
        score; a document that ranks highly in BOTH gets boosted further.
        rrf_k=60 is a commonly used default that dampens the impact of
        any single very-high rank dominating the fusion.
        """
        semantic_ids = self._semantic_search(query, candidate_pool)
        bm25_ids = self._bm25_search(query, candidate_pool)

        fused_scores: Dict[str, float] = {}
        for rank, chunk_id in enumerate(semantic_ids):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (rrf_k + rank + 1)
        for rank, chunk_id in enumerate(bm25_ids):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (rrf_k + rank + 1)

        ranked = sorted(fused_scores.items(), key=lambda x: -x[1])[:top_k]

        results = []
        for chunk_id, score in ranked:
            chunk = self.chunk_by_id[chunk_id]
            results.append({
                "chunk_id": chunk_id,
                "text": chunk["raw_text"],
                "source": chunk["source"],
                "section": chunk["section"],
                "rrf_score": round(score, 4),
                "in_semantic": chunk_id in semantic_ids,
                "in_bm25": chunk_id in bm25_ids,
            })
        return results
