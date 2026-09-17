"""
Boulder Civic AI — ask_boulder.py
Phase 1: retrieval-based Q&A. Replaces ask.py's "paste the whole document
every turn" approach with real retrieval -- each question is embedded,
matched against the chunk index in ChromaDB, and only the top few
relevant chunks are sent to Claude, not the entire corpus.

Same multi-turn conversational shape as ask.py, same behavioral rules
(facts not opinions, honest about single-version limits, decline to
guess when nothing relevant is found) -- but grounded in retrieval
instead of a fixed document paste.

Known simplification for this version: retrieval is based on the user's
latest question only, not the full conversation history. A good enough
starting point -- worth revisiting if follow-up questions ("what about
that one") retrieve poorly without their own context.
"""
import os
import json
from datetime import datetime
import chromadb
from anthropic import Anthropic

client = Anthropic()
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection("boulder_civic")

LOG_FILE = "query_log_boulder.json"
TOP_K = 4  # number of chunks to retrieve per question

SYSTEM_PROMPT = """You are a civic information assistant for Boulder's
civic planning documents. You answer questions using ONLY the retrieved
document excerpts provided in each message -- do not use outside
knowledge about Boulder or general assumptions.

Rules:
1. Answer factual questions using the retrieved excerpts, citing the
   source document and policy/section title for each claim.
2. If asked for an opinion, prediction, or judgment (e.g. "is this a good
   plan", "will this pass", "should this happen"), decline and explain
   that you share facts and citations, not opinions or predictions.
3. If the retrieved excerpts don't clearly address the question, say so
   plainly rather than guessing. If an excerpt is only loosely related,
   say that explicitly rather than presenting it as a direct answer.
4. These documents are static snapshots (BVCP: June 2026 working
   version; Racial Equity Plan: 2021). If asked about current status or
   changes since, say you only have these versions and can't confirm
   anything more recent.
"""

def retrieve(question, top_k=TOP_K):
    results = collection.query(query_texts=[question], n_results=top_k)
    excerpts = []
    for doc_id, text, meta, dist in zip(
        results["ids"][0], results["documents"][0],
        results["metadatas"][0], results["distances"][0]
    ):
        excerpts.append({
            "chunk_id": doc_id,
            "doc": meta["doc"],
            "title": meta["title"],
            "distance": dist,
            "text": text,
        })
    return excerpts

def build_context_block(excerpts):
    parts = []
    for e in excerpts:
        parts.append(
            f"[Source: {e['doc']} — {e['title']} (chunk_id: {e['chunk_id']})]\n{e['text']}"
        )
    return "\n\n---\n\n".join(parts)

def log_turn(user_msg, assistant_msg, retrieved_ids):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user_msg,
        "assistant": assistant_msg,
        "retrieved_chunk_ids": retrieved_ids,
    }
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            log = json.load(f)
    log.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def main():
    print("Boulder Civic AI — ask_boulder.py (Phase 1, retrieval-based Q&A)")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break

        excerpts = retrieve(user_input)
        context_block = build_context_block(excerpts)

        user_message = f"""Retrieved excerpts for this question:

{context_block}

Question: {user_input}"""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        assistant_text = response.content[0].text
        print(f"\nClaude: {assistant_text}\n")

        retrieved_ids = [e["chunk_id"] for e in excerpts]
        print(f"[Retrieved: {', '.join(retrieved_ids)}]\n")

        log_turn(user_input, assistant_text, retrieved_ids)

if __name__ == "__main__":
    main()
