import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chunking.chunker import chunk_text, chunk_records


def test_short_text_is_not_split():
    text = "This is a short paragraph."
    chunks = chunk_text(text, max_chars=800)
    assert chunks == [text]


def test_long_text_is_split_into_multiple_chunks():
    long_text = "\n".join([f"Paragraph number {i} with some content here." for i in range(100)])
    chunks = chunk_text(long_text, max_chars=300, overlap=50)

    assert len(chunks) > 1
    assert all(len(c) <= 300 + 50 for c in chunks)  # allow small slack for overlap carry


def test_chunk_records_attaches_context_header():
    records = [{
        "text": "Body text for the section.",
        "source": "test_doc.md",
        "section": "Section 1",
        "doc_type": "policy",
    }]

    chunks = chunk_records(records)

    assert len(chunks) == 1
    assert "test_doc.md" in chunks[0]["text"]
    assert "Section 1" in chunks[0]["text"]
    assert chunks[0]["chunk_id"] == "chunk_0000"


def test_structured_records_are_not_split():
    """Structured (already-atomic) records should never be chunked further,
    even if long, since splitting a short factual record loses meaning."""
    records = [{
        "text": "A" * 2000,
        "source": "data.json",
        "section": "X01",
        "doc_type": "structured",
    }]

    chunks = chunk_records(records, max_chars=800)

    assert len(chunks) == 1


def test_chunk_ids_are_unique_and_sequential():
    records = [
        {"text": "First.", "source": "a.md", "section": "S1", "doc_type": "policy"},
        {"text": "Second.", "source": "a.md", "section": "S2", "doc_type": "policy"},
    ]
    chunks = chunk_records(records)
    ids = [c["chunk_id"] for c in chunks]
    assert ids == ["chunk_0000", "chunk_0001"]
