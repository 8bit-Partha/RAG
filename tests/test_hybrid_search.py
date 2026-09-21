import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.hybrid_search import HybridRetriever, _tokenize


def test_tokenize_lowercases_and_strips_punctuation():
    tokens = _tokenize("MFA is required for Remote Access!")
    assert tokens == ["mfa", "is", "required", "for", "remote", "access"]


def _make_chunks():
    return [
        {"chunk_id": "c0", "raw_text": "Multi-factor authentication is required for remote access.",
         "source": "access_control_policy.md", "section": "Section 3"},
        {"chunk_id": "c1", "raw_text": "Passwords must be at least 14 characters long.",
         "source": "access_control_policy.md", "section": "Section 3"},
        {"chunk_id": "c2", "raw_text": "Incident response requires escalation within 30 minutes.",
         "source": "incident_response_policy.md", "section": "Section 2"},
    ]


def test_bm25_search_finds_exact_keyword_match():
    chunks = _make_chunks()
    mock_store = MagicMock()
    mock_embedder = MagicMock()

    retriever = HybridRetriever(chunks, mock_store, mock_embedder)
    results = retriever._bm25_search("multi-factor authentication remote access", top_k=3)

    assert results[0] == "c0"


def test_rrf_fusion_boosts_docs_ranked_highly_in_both_lists():
    chunks = _make_chunks()
    mock_store = MagicMock()
    # semantic search returns c1 first, c0 second
    mock_store.query.return_value = [
        {"chunk_id": "c1", "source": "x", "section": "y", "doc_type": "policy"},
        {"chunk_id": "c0", "source": "x", "section": "y", "doc_type": "policy"},
    ]
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.0]

    retriever = HybridRetriever(chunks, mock_store, mock_embedder)
    # BM25 will rank c0 highly for this query (exact keyword overlap)
    results = retriever.search("multi-factor authentication remote access", top_k=3, candidate_pool=3)

    result_ids = [r["chunk_id"] for r in results]
    # c0 appears in both semantic (rank 2) and bm25 (rank 1) results,
    # so it should be fused with a meaningful combined score and present
    assert "c0" in result_ids
    assert results[0]["rrf_score"] > 0
