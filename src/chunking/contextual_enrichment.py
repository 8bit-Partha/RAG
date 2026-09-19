"""
Contextual retrieval for SecuRAG.

Based on Anthropic's Contextual Retrieval technique
(https://www.anthropic.com/news/contextual-retrieval).

The problem it solves: a chunk taken out of its document often loses
meaning that was only clear from surrounding context. For example, the
chunk "It must be renewed within 8 hours" says nothing on its own about
*what* "it" refers to. Structure-aware chunking (chunker.py) already
mitigates this by keeping section boundaries intact, but for longer
documents or documents chunked more aggressively, this stops being
enough.

Contextual retrieval fixes this by asking an LLM, once, for each chunk,
to write a short (1-2 sentence) description of what the chunk is about
*in the context of the full document* -- then prepending that
description to the chunk before embedding and indexing. The chunk stored
for display/generation stays the original text; only the embedded
representation is enriched.

This is an offline, one-time cost at index-build time (proportional to
number of chunks, not number of queries), which is why it's implemented
as a separate optional enrichment step rather than baked into the
embedder -- run it once per corpus rebuild, not per query.
"""

import json
import os
from typing import List, Dict
import anthropic

CONTEXT_PROMPT_TEMPLATE = """<document>
{doc_text}
</document>

Here is a chunk from the above document:
<chunk>
{chunk_text}
</chunk>

Write a short, 1-2 sentence context describing what this chunk is about \
and how it relates to the rest of the document, so that it can be \
correctly understood and searched for on its own. Answer with only the \
context, nothing else."""


class ContextualEnricher:
    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        # A small/cheap model is the right choice here -- this runs once
        # per chunk at index time, and the task (summarize local context)
        # doesn't need a frontier model.
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def _get_document_text(self, source: str, all_chunks: List[Dict]) -> str:
        """Reconstruct the full document text for a given source from its chunks."""
        doc_chunks = [c["raw_text"] for c in all_chunks if c["source"] == source]
        return "\n\n".join(doc_chunks)

    def enrich_chunk(self, chunk: Dict, document_text: str) -> str:
        prompt = CONTEXT_PROMPT_TEMPLATE.format(
            doc_text=document_text[:6000],  # keep prompt cost bounded
            chunk_text=chunk["raw_text"],
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        context = "".join(b.text for b in response.content if b.type == "text").strip()
        return f"{context}\n\n{chunk['raw_text']}"

    def enrich_all(self, chunks: List[Dict]) -> List[Dict]:
        """
        Adds a `contextualized_text` field to every chunk -- this is what
        gets embedded, while `raw_text` (unchanged) is still what's shown
        to the user and passed to generation.
        """
        # Structured records are already atomic and self-describing;
        # contextual enrichment adds little value and isn't worth the
        # API cost for them.
        docs_cache = {}
        enriched = []

        for chunk in chunks:
            if chunk["doc_type"] == "structured":
                chunk["contextualized_text"] = chunk["raw_text"]
                enriched.append(chunk)
                continue

            if chunk["source"] not in docs_cache:
                docs_cache[chunk["source"]] = self._get_document_text(chunk["source"], chunks)

            chunk["contextualized_text"] = self.enrich_chunk(chunk, docs_cache[chunk["source"]])
            enriched.append(chunk)

        return enriched


if __name__ == "__main__":
    with open("data/processed/chunks.json") as f:
        chunks = json.load(f)

    enricher = ContextualEnricher()
    enriched = enricher.enrich_all(chunks)

    with open("data/processed/chunks_contextual.json", "w") as f:
        json.dump(enriched, f, indent=2)

    print(f"Enriched {len(enriched)} chunks. Example:\n")
    print(enriched[1]["contextualized_text"])
