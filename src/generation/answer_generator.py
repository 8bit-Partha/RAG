"""
Answer generation for SecuRAG.

Two design choices here matter more than the API call itself:

1. The prompt explicitly forces the model to cite [source] for every
   claim and to say it doesn't know rather than guess when the retrieved
   context doesn't cover the question. In a security/compliance domain,
   a confident wrong answer is worse than no answer.
2. We pass the retrieved chunks as clearly delimited, labeled context --
   not just concatenated text -- so the model can attribute each part of
   its answer to a specific source document and section.
"""

import os
from typing import List, Dict
import anthropic

SYSTEM_PROMPT = """You are a cybersecurity knowledge assistant. Answer the \
user's question using ONLY the provided context excerpts below.

Rules:
- Every factual claim in your answer must be followed by a citation in \
the form [source: section], using the source and section labels given \
in the context.
- If the context does not contain enough information to answer the \
question, say so explicitly rather than guessing or using outside \
knowledge.
- Be concise and direct. Do not pad the answer with generic security \
advice that isn't grounded in the provided context.
"""


class AnswerGenerator:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def _format_context(self, chunks: List[Dict]) -> str:
        blocks = []
        for c in chunks:
            blocks.append(
                f"---\nSource: {c['source']} | Section: {c['section']}\n{c['text']}"
            )
        return "\n".join(blocks)

    def generate(self, query: str, chunks: List[Dict]) -> Dict:
        context = self._format_context(chunks)

        user_message = f"Context excerpts:\n{context}\n\nQuestion: {query}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        answer_text = "".join(
            block.text for block in response.content if block.type == "text"
        )

        return {
            "answer": answer_text,
            "sources": [
                {"source": c["source"], "section": c["section"]} for c in chunks
            ],
        }
