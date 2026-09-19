"""
Cross-encoder re-ranking for SecuRAG.

Initial retrieval (semantic + BM25) is fast but approximate -- it scores
each candidate independently of the query in a shared vector space. A
cross-encoder instead looks at the query and each candidate TOGETHER in
one forward pass, which is far more accurate but too slow to run over an
entire corpus. So the pattern is: retrieve a wider candidate pool cheaply
(~20 chunks), then re-rank only those with the cross-encoder, then keep
the true top-k.
"""

from typing import List, Dict

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker:
    def __init__(self, model_name: str = MODEL_NAME):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
        if not candidates:
            return []

        pairs = [(query, c["text"]) for c in candidates]
        scores = self.model.predict(pairs)

        for c, score in zip(candidates, scores):
            c["rerank_score"] = float(score)

        reranked = sorted(candidates, key=lambda c: -c["rerank_score"])
        return reranked[:top_k]
