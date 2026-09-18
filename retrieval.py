"""
Boulder Civic AI — retrieval.py
Shared retrieval logic for both ask_boulder.py and eval_harness.py, so
comparing retrieval methods doesn't mean duplicating query logic in two
places.

Two methods:
  - retrieve_semantic: pure embedding similarity (what Phase 1 used)
  - retrieve_hybrid: semantic similarity + exact keyword overlap, combined

Hybrid approach: pull a wider candidate pool via semantic search (15
chunks, not just the final top_k), score each candidate on both semantic
similarity and keyword overlap with the question, then re-rank by a
weighted combination and return the top_k. This lets an exact term
match (e.g. "Blue Line") pull a chunk up even if its pure embedding
distance wasn't the closest.
"""
import re
import chromadb

DB_PATH = "chroma_db"
COLLECTION_NAME = "boulder_civic"

chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection = chroma_client.get_collection(COLLECTION_NAME)

STOPWORDS = {"what", "does", "plan", "about", "this", "that", "with", "have",
             "from", "they", "which", "should", "current", "status"}

def _extract_keywords(text):
    words = re.findall(r'[a-zA-Z]{4,}', text.lower())
    return [w for w in words if w not in STOPWORDS]

def retrieve_semantic(question, top_k=4):
    results = collection.query(query_texts=[question], n_results=top_k)
    return _format_results(results)

def retrieve_hybrid(question, top_k=4, candidate_pool=15, alpha=0.6):
    """
    alpha: weight given to semantic similarity vs. keyword overlap.
    alpha=1.0 is equivalent to pure semantic; alpha=0.0 is pure keyword.
    0.6 gives semantic similarity more weight but lets strong keyword
    matches meaningfully change the ranking.
    """
    results = collection.query(query_texts=[question], n_results=candidate_pool)
    candidates = _format_results(results)
    if not candidates:
        return []

    keywords = _extract_keywords(question)

    distances = [c["distance"] for c in candidates]
    min_d, max_d = min(distances), max(distances)
    d_range = (max_d - min_d) or 1e-9

    for c in candidates:
        semantic_sim = 1 - (c["distance"] - min_d) / d_range  # 0..1, higher = better
        text_lower = c["text"].lower()
        keyword_hits = sum(1 for kw in keywords if kw in text_lower)
        keyword_score = keyword_hits / len(keywords) if keywords else 0
        c["combined_score"] = alpha * semantic_sim + (1 - alpha) * keyword_score

    candidates.sort(key=lambda c: c["combined_score"], reverse=True)
    return candidates[:top_k]

def _format_results(results):
    excerpts = []
    for doc_id, text, meta, dist in zip(
        results["ids"][0], results["documents"][0],
        results["metadatas"][0], results["distances"][0]
    ):
        excerpts.append({
            "chunk_id": doc_id,
            "doc": meta["doc"],
            "title": meta["title"],
            "unit_id": meta["unit_id"],
            "distance": dist,
            "text": text,
        })
    return excerpts
