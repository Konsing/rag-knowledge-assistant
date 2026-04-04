"""
Retrieval quality evaluation script.

Tests retrieval quality with hardcoded questions and expected
section keywords. Measures whether the right chunks surface
for each question.

Usage:
    docker compose exec backend python eval/eval_retrieval.py
"""

import sys
import os

# Support running from project root (outside Docker) or from /app (inside Docker)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.join(_script_dir, "..", "backend")
if os.path.isdir(_backend_dir):
    sys.path.insert(0, _backend_dir)
else:
    # Inside Docker: /app is the backend root, eval/ is mounted at /app/eval/
    sys.path.insert(0, os.path.join(_script_dir, ".."))

from app.embedding.embedder import embed_query
from app.retrieval.search import search, get_collection_info


# Each test case: question + keywords we expect in the retrieved chunks.
# A "hit" means at least one top-k chunk contains one of the expected keywords
# (matched case-insensitively against section title OR chunk text).
TEST_CASES = [
    {
        "question": "What translation methods were compared in the experiments?",
        "expected_keywords": ["baseline", "google", "deepl", "tencent", "compare"],
    },
    {
        "question": "What is the main contribution of this paper?",
        "expected_keywords": ["introduction", "contribution", "propose", "main"],
    },
    {
        "question": "What datasets were used for evaluation?",
        "expected_keywords": ["dataset", "test set", "evaluation", "wmt", "flores"],
    },
    {
        "question": "How does ChatGPT perform on multilingual translation?",
        "expected_keywords": ["multilingual", "language", "chinese", "german", "romanian"],
    },
    {
        "question": "What are the limitations of the approach?",
        "expected_keywords": ["limitation", "weakness", "shortcoming", "fail"],
    },
    {
        "question": "What prompts were used for translation?",
        "expected_keywords": ["prompt", "template", "translate", "instruction"],
    },
    {
        "question": "How robust is the translation quality?",
        "expected_keywords": ["robust", "noise", "error", "quality"],
    },
    {
        "question": "What did the human evaluation reveal?",
        "expected_keywords": ["human", "analysis", "annotator", "manual", "evaluation"],
    },
    {
        "question": "What pivot prompting strategy was proposed?",
        "expected_keywords": ["pivot", "prompting", "intermediate", "strategy"],
    },
    {
        "question": "What were the main findings and conclusions?",
        "expected_keywords": ["conclusion", "finding", "result", "summary"],
    },
]


def check_hit(results: list[dict], expected_keywords: list[str]) -> bool:
    """Check if any top-k result contains at least one expected keyword."""
    for r in results:
        text = r["text"].lower()
        section = r["metadata"]["section_title"].lower()
        combined = text + " " + section

        for kw in expected_keywords:
            if kw.lower() in combined:
                return True
    return False


def run_evaluation(top_k: int = 5, verbose: bool = True) -> dict:
    """
    Run the retrieval quality assessment.

    Returns dict with precision score and per-question results.
    """
    info = get_collection_info()
    if info["points_count"] == 0:
        print("ERROR: No documents in the knowledge base. Ingest some papers first.")
        print("  Example: curl -X POST http://localhost:8000/api/ingest -F 'arxiv_url=https://arxiv.org/abs/2301.08745'")
        return {"precision": 0.0, "results": []}

    print(f"Collection: {info['name']} ({info['points_count']} chunks)")
    print(f"Running {len(TEST_CASES)} test queries (top_k={top_k})...")
    print("=" * 70)

    hits = 0
    results = []

    for i, tc in enumerate(TEST_CASES, 1):
        query_vector = embed_query(tc["question"])
        search_results = search(query_vector, top_k=top_k)

        is_hit = check_hit(search_results, tc["expected_keywords"])
        if is_hit:
            hits += 1

        result = {
            "question": tc["question"],
            "hit": is_hit,
            "top_sections": [r["metadata"]["section_title"] for r in search_results[:3]],
            "top_scores": [round(r["score"], 3) for r in search_results[:3]],
        }
        results.append(result)

        if verbose:
            status = "HIT" if is_hit else "MISS"
            print(f"\n[{i:2d}] [{status}] {tc['question']}")
            for j, r in enumerate(search_results[:3]):
                print(f"     [{j+1}] score={r['score']:.3f} section=\"{r['metadata']['section_title']}\"")

    precision = hits / len(TEST_CASES)

    print("=" * 70)
    print(f"\nRetrieval Precision: {hits}/{len(TEST_CASES)} = {precision:.1%}")
    print(f"  Hits: {hits}  |  Misses: {len(TEST_CASES) - hits}")

    if precision < 0.7:
        print("\n  WARNING: Precision below 70%. Consider:")
        print("  - Adjusting chunk size/overlap")
        print("  - Improving section detection")
        print("  - Lowering score_threshold")
    elif precision >= 0.9:
        print("\n  Excellent retrieval quality!")

    return {"precision": precision, "hits": hits, "total": len(TEST_CASES), "results": results}


if __name__ == "__main__":
    run_evaluation()
