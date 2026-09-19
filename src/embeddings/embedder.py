"""
Embedding generation for SecuRAG.

Uses a local sentence-transformers model (BAAI/bge-small-en-v1.5) so the
project runs fully offline with no embedding API cost. Swap MODEL_NAME
for a larger BGE variant or a hosted embedding API (Voyage, OpenAI) if you
want higher retrieval quality at the cost of a network dependency.

BGE models expect a query-side instruction prefix for best results --
that's the `QUERY_PREFIX` below. Document-side text is embedded as-is.
"""

from typing import List
import numpy as np

MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder:
    def __init__(self, model_name: str = MODEL_NAME):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        """Embed a batch of document chunks."""
        return self.model.encode(
            texts,
            normalize_embeddings=True,   # so cosine similarity == dot product
            show_progress_bar=True,
            batch_size=32,
        )

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single user query, with the BGE query instruction prefix."""
        return self.model.encode(
            QUERY_PREFIX + query,
            normalize_embeddings=True,
        )


if __name__ == "__main__":
    import json

    with open("data/processed/chunks.json") as f:
        chunks = json.load(f)

    embedder = Embedder()
    texts = [c["raw_text"] for c in chunks]
    vectors = embedder.embed_documents(texts)

    print(f"Embedded {len(texts)} chunks -> shape {vectors.shape}")

    query_vec = embedder.embed_query("How long can temporary access last?")
    sims = vectors @ query_vec
    top_idx = np.argsort(-sims)[:3]

    print("\nTop matches for 'How long can temporary access last?':")
    for i in top_idx:
        print(f"  [{sims[i]:.3f}] {chunks[i]['source']} / {chunks[i]['section']}")
