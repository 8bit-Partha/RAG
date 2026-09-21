"""
Evaluation for SecuRAG.

Measures retrieval and generation SEPARATELY, which is the key idea to
get right when debugging RAG quality:

  - Retrieval hit rate: did the correct source document show up in the
    top-k retrieved chunks at all? If this is low, the problem is in
    chunking/embedding/search -- fixing the prompt won't help.
  - Answer groundedness (simple proxy): does the generated answer cite
    the expected source? If retrieval succeeds but this is low, the
    problem is in the generation prompt, not retrieval.

This is a lightweight, dependency-free evaluator you can run without an
API key (retrieval-only) or with one (full pipeline). For a more rigorous
evaluation, swap in the `ragas` library, which adds LLM-graded metrics
like faithfulness and context precision -- see the README for notes on
that upgrade path.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import SecuRAGPipeline


def evaluate(run_generation: bool = True):
    with open("eval/test_questions.json") as f:
        test_set = json.load(f)

    pipeline = SecuRAGPipeline()

    retrieval_hits = 0
    generation_hits = 0
    results = []

    for case in test_set:
        candidates = pipeline.retriever.search(case["question"], top_k=15)
        top_chunks = pipeline.reranker.rerank(case["question"], candidates, top_k=5)

        retrieved_sources = {(c["source"], c["section"]) for c in top_chunks}
        expected = (case["expected_source"], case["expected_section"])
        retrieval_hit = expected in retrieved_sources
        retrieval_hits += retrieval_hit

        row = {
            "question": case["question"],
            "expected": f"{expected[0]} / {expected[1]}",
            "retrieval_hit": retrieval_hit,
        }

        if run_generation:
            gen_result = pipeline.generator.generate(case["question"], top_chunks)
            cited_sources = {(s["source"], s["section"]) for s in gen_result["sources"]}
            generation_hit = expected in cited_sources
            generation_hits += generation_hit
            row["generation_hit"] = generation_hit
            row["answer"] = gen_result["answer"][:150] + "..."

        results.append(row)

    n = len(test_set)
    print(f"\n{'='*60}")
    print(f"Retrieval hit rate: {retrieval_hits}/{n} ({100*retrieval_hits/n:.0f}%)")
    if run_generation:
        print(f"Generation groundedness: {generation_hits}/{n} ({100*generation_hits/n:.0f}%)")
    print(f"{'='*60}\n")

    for r in results:
        status = "PASS" if r["retrieval_hit"] else "FAIL"
        print(f"[{status}] {r['question']}")
        print(f"    expected: {r['expected']}")

    with open("eval/results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nDetailed results saved to eval/results.json")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-generation", action="store_true",
                         help="Only evaluate retrieval (no API key needed)")
    args = parser.parse_args()
    evaluate(run_generation=not args.no_generation)
