"""
Chunking for SecuRAG.

The ingestion layer already splits documents along their natural
structure (sections, pages, records). This module's job is narrower:
if any single section is still too long to embed/retrieve well, split
it further -- but keep the original section/source metadata attached to
every resulting piece, and prefix each chunk with a small context header.

That header trick (repeating "Source / Section" at the top of every
chunk) is the single highest-leverage fix for a common RAG failure mode:
a chunk that reads fine in isolation but has lost the heading that gave
it meaning (e.g. a chunk that says "must be revoked within 24 hours"
with no indication that it's about access, not incidents).
"""

from typing import List, Dict


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping windows on paragraph boundaries where
    possible, falling back to hard character splits for very long
    unbroken paragraphs.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p for p in text.split("\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 1 <= max_chars:
            current = f"{current}\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # carry overlap forward from the tail of the previous chunk
            tail = current[-overlap:] if current else ""
            current = f"{tail}\n{para}" if tail else para

            # a single paragraph longer than max_chars: hard split it
            while len(current) > max_chars:
                chunks.append(current[:max_chars])
                current = current[max_chars - overlap:]

    if current:
        chunks.append(current)

    return chunks


def chunk_records(records: List[Dict], max_chars: int = 800, overlap: int = 100) -> List[Dict]:
    """
    Apply chunk_text to every ingested record, attaching a context header
    and a stable chunk_id used later for citations and eval.
    """
    chunks = []
    chunk_counter = 0

    for record in records:
        # Structured records (e.g. threat tactic definitions) are already
        # short, atomic, and meaningful on their own -- don't split them.
        if record["doc_type"] == "structured":
            pieces = [record["text"]]
        else:
            pieces = chunk_text(record["text"], max_chars=max_chars, overlap=overlap)

        for i, piece in enumerate(pieces):
            header = f"[{record['source']} | {record['section']}]"
            chunk_text_with_header = f"{header}\n{piece}"

            chunks.append({
                "chunk_id": f"chunk_{chunk_counter:04d}",
                "text": chunk_text_with_header,
                "raw_text": piece,
                "source": record["source"],
                "section": record["section"],
                "doc_type": record["doc_type"],
                "part": f"{i + 1}/{len(pieces)}" if len(pieces) > 1 else "1/1",
            })
            chunk_counter += 1

    return chunks


if __name__ == "__main__":
    import json
    import sys
    sys.path.insert(0, "src")
    from ingestion.document_loader import load_directory

    records = load_directory("data/raw")
    chunks = chunk_records(records)

    print(f"{len(records)} records -> {len(chunks)} chunks")
    for c in chunks[:3]:
        print(f"\n--- {c['chunk_id']} ({c['doc_type']}, part {c['part']}) ---")
        print(c["text"][:200])

    with open("data/processed/chunks.json", "w") as f:
        json.dump(chunks, f, indent=2)
    print(f"\nSaved {len(chunks)} chunks to data/processed/chunks.json")
