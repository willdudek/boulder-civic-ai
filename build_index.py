"""
Boulder Civic AI — build_index.py
Phase 1: embed all chunks and store them in ChromaDB for retrieval.

Uses ChromaDB's default embedding model (all-MiniLM-L6-v2, downloaded
automatically on first run) -- free, runs locally, no API key or cost.
This is a deliberate choice: embeddings don't need Claude's intelligence,
just a good semantic representation, so there's no reason to spend API
credits on this step.

Follows the "rebuild from scratch" convention used throughout this
project: every run wipes and recreates the collection from the current
chunks.json, rather than incrementally patching it. Since chunking is
deterministic and cheap to re-run, there's no risk in always rebuilding
fresh -- it guarantees the index never drifts from the current chunk set.

Usage:
    python3 build_index.py
"""
import json
import chromadb

CHUNKS_PATH = "data/chunks/chunks.json"
DB_PATH = "chroma_db"
COLLECTION_NAME = "boulder_civic"

def main():
    with open(CHUNKS_PATH) as f:
        chunks = json.load(f)

    client = chromadb.PersistentClient(path=DB_PATH)

    # Full rebuild every run -- delete the old collection if it exists,
    # so the index always reflects exactly what's in chunks.json right now.
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(COLLECTION_NAME)

    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "doc": c["doc"],
            "unit_type": c["unit_type"],
            "unit_id": str(c["unit_id"]),
            "title": c.get("title", ""),
        }
        for c in chunks
    ]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"Embedded and stored {len(chunks)} chunks in ChromaDB.")
    print(f"Location: {DB_PATH}/  |  Collection: {COLLECTION_NAME}")

if __name__ == "__main__":
    main()
