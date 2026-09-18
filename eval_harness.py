"""
Boulder Civic AI — eval_harness.py
Phase 2: automated retrieval evaluation.

Runs every question in eval_questions.csv through retrieval (via the
shared retrieval.py module) and checks whether the retrieved chunks
match each question's expected_location. Writes results to a
timestamped, method-labeled CSV, so different retrieval methods can be
run and compared side by side without overwriting each other.

Usage:
    python3 eval_harness.py semantic
    python3 eval_harness.py hybrid
"""
import csv
import re
import sys
from datetime import datetime
import retrieval

EVAL_QUESTIONS_PATH = "eval_questions.csv"
EMBEDDING_MODEL = "all-MiniLM-L6-v2 (ChromaDB default)"

def check_match(expected_location, retrieved):
    if not expected_location or expected_location.strip().upper() == "N/A":
        return None, None, None

    expected_lower = expected_location.lower()
    expected_digits = re.findall(r'\d+', expected_location)

    for rank, chunk in enumerate(retrieved, start=1):
        if expected_digits and str(chunk["unit_id"]) in expected_digits:
            return True, rank, chunk["chunk_id"]
        title_lower = str(chunk["title"]).lower()
        keywords = [w for w in re.findall(r'[a-z]{4,}', expected_lower)
                    if w not in ("policy", "glossary", "chapter", "section")]
        if any(kw in title_lower for kw in keywords):
            return True, rank, chunk["chunk_id"]

    return False, None, None

def main():
    method = sys.argv[1] if len(sys.argv) > 1 else "semantic"
    if method not in ("semantic", "hybrid"):
        print("Usage: python3 eval_harness.py [semantic|hybrid]")
        sys.exit(1)

    retrieve_fn = retrieval.retrieve_semantic if method == "semantic" else retrieval.retrieve_hybrid

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"eval_results_{method}_{run_id}.csv"

    with open(EVAL_QUESTIONS_PATH, newline="") as f:
        eval_rows = list(csv.DictReader(f))

    results = []
    for row in eval_rows:
        question = row["question"]
        expected_location = row["expected_location"]
        retrieved = retrieve_fn(question)

        matched, rank, matched_chunk_id = check_match(expected_location, retrieved)

        results.append({
            "run_id": run_id,
            "retrieval_method": method,
            "embedding_model": EMBEDDING_MODEL,
            "question_id": row["id"],
            "question": question,
            "question_type": row["question_type"],
            "expected_doc": row["expected_doc"],
            "expected_location": expected_location,
            "matched": matched if matched is not None else "N/A",
            "matched_rank": rank if rank else "",
            "matched_chunk_id": matched_chunk_id if matched_chunk_id else "",
            "retrieved_chunk_ids": "; ".join(c["chunk_id"] for c in retrieved),
            "notes": "review manually -- opinion/out-of-scope question" if matched is None else "",
        })

    fieldnames = list(results[0].keys())
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    applicable = [r for r in results if r["matched"] != "N/A"]
    passed = sum(1 for r in applicable if r["matched"])
    print(f"[{method}] Ran {len(results)} questions ({len(applicable)} retrieval-checkable)")
    print(f"[{method}] Retrieval match: {passed}/{len(applicable)}")
    print(f"Results written to {output_path}")

if __name__ == "__main__":
    main()
