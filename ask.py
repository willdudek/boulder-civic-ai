"""
Boulder Civic AI — ask.py
Phase 0 experiment: naive full-context Q&A, no retrieval yet.
Loads the entire extracted BVCP text into the system prompt and lets
Claude answer directly against it, multi-turn. This is the baseline
we're testing before building the chunking/retrieval pipeline.
"""
import os
import json
from datetime import datetime
from anthropic import Anthropic

client = Anthropic()  # reads ANTHROPIC_API_KEY from env

DOC_PATH = "data/processed/bvcp_full_text.txt"
LOG_FILE = "query_log.json"

def load_document():
    with open(DOC_PATH, "r") as f:
        return f.read()

def build_system_prompt(document_text):
    return f"""You are a civic information assistant for Boulder's 2026
Comprehensive Plan update (BVCP). You answer questions using ONLY the
document text provided below — do not use outside knowledge about Boulder
or general assumptions about what the plan might say.

Rules:
1. Answer factual questions about what the plan says, citing the specific
   policy number and/or page when possible.
2. If asked for an opinion, prediction, or judgment (e.g. "is this a good
   plan", "will this pass", "should this happen"), decline and explain
   that you share facts and citations, not opinions or predictions.
3. If the document doesn't clearly address the question, say so plainly
   rather than guessing. If there's a related but not directly on-point
   section, say that explicitly and point to it rather than presenting it
   as a direct answer.
4. This document is a single working version (June 2026) of a plan that
   is still mid-adoption — some provisions (e.g. the airport language)
   were still contested and unresolved as of this version. If asked about
   something that might have changed since, say you only have this one
   version and can't confirm current status.

--- DOCUMENT TEXT ---
{document_text}
--- END DOCUMENT TEXT ---
"""

def log_turn(user_msg, assistant_msg):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user_msg,
        "assistant": assistant_msg,
    }
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            log = json.load(f)
    log.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def main():
    print("Loading document...")
    document_text = load_document()
    system_prompt = build_system_prompt(document_text)
    print(f"Loaded. System prompt is ~{len(system_prompt)//4} tokens.\n")

    history = []
    print("Boulder Civic AI — ask.py (Phase 0, naive full-context Q&A)")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break

        history.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=system_prompt,
            messages=history,
        )

        assistant_text = response.content[0].text
        print(f"\nClaude: {assistant_text}\n")

        history.append({"role": "assistant", "content": assistant_text})
        log_turn(user_input, assistant_text)

if __name__ == "__main__":
    main()
