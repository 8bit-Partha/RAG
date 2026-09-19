"""
Vector store wrapper around ChromaDB for SecuRAG.

Chroma is used here because it runs embedded (no separate server process),
which keeps the project easy to clone and run. If you outgrow it -- larger
corpora, need for a hosted/production deployment -- the same interface
(add / query) maps cleanly onto Qdrant or Weaviate later; only this file
would need to change.
"""

from typing import List, Dict
import chromadb


class VectorStore:
    def __init__(self, persist_dir: str = "data/processed/chroma_db", collection_name: str = "securag"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: List[Dict], embeddings) -> None:
        """
        chunks: list of chunk dicts (from chunker.py), each with chunk_id,
        text, source, section, doc_type.
        embeddings: numpy array aligned 1:1 with chunks.
        """
        self.collection.add(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=embeddings.tolist(),
            documents=[c["text"] for c in chunks],
            metadatas=[
                {
                    "source": c["source"],
                    "section": c["section"],
                    "doc_type": c["doc_type"],
                }
                for c in chunks
            ],
        )

    def query(self, query_embedding, top_k: int = 10, doc_type_filter: str = None) -> List[Dict]:
        """
        Semantic search. Returns chunks ordered by similarity, each with
        its distance score and metadata attached -- everything needed to
        build a citation later.
        """
        where = {"doc_type": doc_type_filter} if doc_type_filter else None

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where,
        )

        hits = []
        for i in range(len(results["ids"][0])):
            hits.append({
                "chunk_id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "score": 1 - results["distances"][0][i],  # convert distance -> similarity
                **results["metadatas"][0][i],
            })
        return hits

    def count(self) -> int:
        return self.collection.count()


if __name__ == "__main__":
    import json
    from src.embeddings.embedder import Embedder

    with open("data/processed/chunks.json") as f:
        chunks = json.load(f)

    embedder = Embedder()
    vectors = embedder.embed_documents([c["raw_text"] for c in chunks])

    store = VectorStore()
    store.add_chunks(chunks, vectors)
    print(f"Indexed {store.count()} chunks into Chroma")

    query_vec = embedder.embed_query("What MFA requirements apply to remote access?")
    for hit in store.query(query_vec, top_k=3):
        print(f"  [{hit['score']:.3f}] {hit['source']} / {hit['section']}")
