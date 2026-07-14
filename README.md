# Boulder Civic AI

A RAG-based Q&A tool over Boulder's civic planning process — the
unstructured-data companion to the nba-analytics project's structured stack.

## Status
Phase 0: complete. Phase 1 (corpus expansion) in progress — extraction
pipeline generalized and validated across two documents.

## Problem
[Fill in: the "why" — hard to know what's in a 100+ page civic document,
hard to track what changed and when, hard to know how to get involved.]

## Architecture
[Fill in as built: chunking strategy, ChromaDB, structured lookup, frontend.]

## Source & Versioning
Primary source: Boulder Valley Comprehensive Plan (BVCP), June 2026 working
version — plan was still mid-adoption as of this version (Planning
Commission approved June 17; a specific airport-related provision was sent
back to Planning Board after a June 25 City Council session; final
City Council / Board of County Commissioners votes not yet reflected).
Version drift handling: [fill in during Phase 3]

## What this tool does / doesn't do
- Answers factual questions about the plan's contents, grounded in citations
- Does not offer opinions, predictions, or judgments about the plan
- [expand as scope solidifies]

## Phase 0 Findings

**What was tested:** A naive baseline — the entire extracted BVCP text
(~54K tokens) loaded directly into a system prompt, no chunking or
retrieval, multi-turn Q&A via `ask.py`. Goal: establish whether the
chunking/retrieval pipeline solves a real problem before building it.

**Extraction note:** Initial PDF text extraction (pdfplumber default mode)
silently interleaved text from adjacent policies due to the document's
multi-column layout — a real data-quality bug that would have corrupted
any downstream pipeline, chunked or not. Fixed by switching to PyMuPDF,
which preserves correct reading order on this document by default.

**Test results (naive full-context Q&A, single document):**

- Direct factual question (affordable housing policies): clean, accurate
- Personal/out-of-scope question (home buying advice): correctly deflected
  to a professional, cited limited relevant stats
- Opinion-bait ("is this a good plan?"): correctly declined to opine, gave
  neutral factual context
- Version-drift / structural limit (airport policy status): correctly
  identified it only has one static version, cited the relevant policy
  (79), did not fabricate a "current status," pointed to real external
  sources

**Conclusion:** For a single, well-structured document, naive full-context
Q&A performed well across all four test cases — no clear failure found.
This reframes the justification for Phase 1: the case for chunking +
retrieval isn't "the naive approach doesn't work" on one document, it's:

- **Scale** — untested whether quality holds as more documents (minutes,
  prior plans, hearing records) are added to context at once
- **True version comparison** — naive Q&A can honestly say "I can't
  compare versions," but structurally cannot ever answer "what changed
  in Policy 27" with only one document loaded; that requires multiple
  tagged versions and retrieval
- **Evaluability** — no measurable retrieval step exists to score, which
  Phase 2's evaluation work depends on

## Extraction Pipeline Notes

`extract_text.py` (PyMuPDF-based) is generalized to handle any PDF in the
corpus, taking input/output paths as arguments rather than being hardcoded
per document. Quirks found and fixed so far, all handled automatically
without manual page inspection:

- **Multi-column reading order** — some pages read columns in raster-scan
  order rather than top-to-bottom per column, interleaving text from
  adjacent sections. PyMuPDF's default extraction handles this correctly
  on documents seen so far.
- **Decorative letter-spaced headings** — stylized section titles (e.g.
  "A c k n o w l e d g e m e n t s") extract as space-separated single
  letters rather than words. Fixed via a regex post-processing pass
  applied to the whole document.
- **Image-heavy / low-text pages** — pages with fewer than 10 extractable
  words are auto-flagged with a placeholder noting the page likely has
  visual content not captured in the text extract, rather than silently
  producing missing or empty content.

**Corpus so far:**

- BVCP (June 2026): 69 pages, 217,177 characters, ~54,300 tokens
- Racial Equity Plan (2021): 43 pages, 112,263 characters, ~28,065 tokens

Combined (~82K tokens) still technically fits in a single context window,
but is approaching the point where naive full-context Q&A becomes
unwieldy and expensive — a real, observed data point motivating the move
to chunking + retrieval (Phase 1) rather than an assumed one.

**Next step:** Phase 1 — chunking and ChromaDB, starting with the BVCP
before expanding the corpus further.
