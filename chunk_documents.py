"""
Boulder Civic AI — chunk_documents.py
Phase 1: split processed documents into structure-aware chunks with metadata.

BVCP: chunked by numbered policy (Chapter 3) and by future land use
designation (Chapter 4). Other chapters chunk by page-group fallback,
since they lack a consistent numbered structure.

Racial Equity Plan: lacks BVCP's clean numbering, so this is chunked by
page-group fallback throughout. This is a real tradeoff, not a hidden
gap -- worth revisiting if retrieval quality on this document is weak.

Output: data/chunks/chunks.json -- a list of chunk objects, each with
metadata (doc, unit_type, unit_id, page range) and the chunk's text.
"""
import re
import json
import os

CHUNKS_OUTPUT = "data/chunks/chunks.json"

# BVCP's 12 future land use designation names (Chapter 4), in document order
FLU_DESIGNATIONS = [
    "Neighborhood 1", "Neighborhood 2", "Community Hub", "Regional Hub",
    "Innovation and Production Hub", "Parks", "Greenways", "Open Space",
    "Industrial", "Facilities", "University", "Rural Lands",
]

POLICY_HEADER_RE = re.compile(r'^(\d{1,3})\.\s+(.+)$', re.MULTILINE)
PAGE_MARKER_RE = re.compile(r'--- Page (\d+) ---')

def split_into_pages(raw_text):
    """Split raw extracted text into a list of (page_num, page_text) tuples."""
    pages = []
    matches = list(PAGE_MARKER_RE.finditer(raw_text))
    for i, m in enumerate(matches):
        page_num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        pages.append((page_num, raw_text[start:end].strip()))
    return pages

def chunk_bvcp_policies(full_text, doc_name):
    """Chunk Chapter 3 policies by numbered header. Returns (chunks, matched_span)."""
    chunks = []
    matches = list(POLICY_HEADER_RE.finditer(full_text))
    # Only trust matches that look like real policy headers (1-104), not
    # stray numbers elsewhere in the text.
    policy_matches = [m for m in matches if 1 <= int(m.group(1)) <= 104]

    for i, m in enumerate(policy_matches):
        policy_num = int(m.group(1))
        title = m.group(2).strip()
        start = m.start()
        end = policy_matches[i + 1].start() if i + 1 < len(policy_matches) else None
        text_block = full_text[start:end] if end else full_text[start:start + 800]

        chunks.append({
            "chunk_id": f"bvcp_policy_{policy_num}",
            "doc": doc_name,
            "unit_type": "policy",
            "unit_id": policy_num,
            "title": title,
            "text": text_block.strip(),
        })
    return chunks

def chunk_bvcp_flu(full_text, doc_name):
    """Chunk Chapter 4 by future land use designation name."""
    chunks = []
    positions = []
    for name in FLU_DESIGNATIONS:
        idx = full_text.find(f"\n{name}\n")
        if idx == -1:
            idx = full_text.find(name)
        if idx != -1:
            positions.append((idx, name))
    positions.sort()

    for i, (start, name) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else start + 3000
        chunks.append({
            "chunk_id": f"bvcp_flu_{name.lower().replace(' ', '_')}",
            "doc": doc_name,
            "unit_type": "future_land_use",
            "unit_id": name,
            "title": name,
            "text": full_text[start:end].strip(),
        })
    return chunks

def chunk_by_pages(pages, doc_name, pages_per_chunk=3):
    """Fallback: group N pages per chunk, tagging the page range."""
    chunks = []
    for i in range(0, len(pages), pages_per_chunk):
        group = pages[i:i + pages_per_chunk]
        page_nums = [p[0] for p in group]
        text = "\n\n".join(p[1] for p in group)
        if not text.strip():
            continue
        chunks.append({
            "chunk_id": f"{doc_name.lower().replace(' ', '_')}_pages_{page_nums[0]}-{page_nums[-1]}",
            "doc": doc_name,
            "unit_type": "page_group",
            "unit_id": f"{page_nums[0]}-{page_nums[-1]}",
            "title": f"Pages {page_nums[0]}-{page_nums[-1]}",
            "text": text.strip(),
        })
    return chunks

def process_bvcp(path):
    with open(path, "r") as f:
        raw = f.read()
    pages = split_into_pages(raw)

    # Chapter 3 (Policies) and Chapter 4 (Future Land Use) page ranges,
    # confirmed directly from the extracted text's physical page markers
    # (grep -n "CHAPTER" / chapter titles against bvcp_full_text.txt).
    # NOTE: these differ from the PDF's printed table-of-contents numbers
    # (51-76, 77-121) because each physical PDF page is a two-page spread --
    # printed page numbers run roughly 2x the physical page markers.
    policy_pages = [p for p in pages if 26 <= p[0] <= 38]
    flu_pages = [p for p in pages if 39 <= p[0] <= 61]
    other_pages = [p for p in pages if not (26 <= p[0] <= 61)]

    policy_text = "\n".join(p[1] for p in policy_pages)
    flu_text = "\n".join(p[1] for p in flu_pages)

    chunks = []
    chunks += chunk_bvcp_policies(policy_text, "BVCP")
    chunks += chunk_bvcp_flu(flu_text, "BVCP")
    chunks += chunk_by_pages(other_pages, "BVCP_other")
    return chunks

def process_racial_equity_plan(path):
    """
    Hybrid chunking: confirmed section headers (verified against the real
    body text, not just the table of contents) become their own chunks.
    Everything else falls back to page-grouping -- but only for pages not
    already covered by a confirmed section, to avoid duplicate content.
    """
    with open(path, "r") as f:
        raw = f.read()
    pages = split_into_pages(raw)
    full_text = "\n".join(p[1] for p in pages)

    # Confirmed top-level section headers (verified in body text via grep,
    # not assumed from the table of contents). Some wrap across two lines,
    # possibly with trailing whitespace on either line -- matched via
    # regex rather than an exact string, since exact matches are fragile
    # against small whitespace differences in the extracted text.
    SECTION_HEADER_PATTERNS = [
        (r'The Journey Here', "The Journey Here"),
        (r'Timeline of Work To Date', "Timeline of Work To Date"),
        (r'Community Feedback on the\s*\n\s*Racial Equity Plan Outline',
         "Community Feedback on the Racial Equity Plan Outline"),
        (r'Planning Timeframe and Tracking Progress', "Planning Timeframe and Tracking Progress"),
    ]
    GOAL_HEADER_RE = re.compile(r'^Goal \d\s+— .+$', re.MULTILINE)

    positions = []  # (start_index, chunk_id, title)
    for pattern, title in SECTION_HEADER_PATTERNS:
        m = re.search(pattern, full_text)
        if m:
            positions.append((m.start(), title.lower().replace(" ", "_")[:40], title))
    for m in GOAL_HEADER_RE.finditer(full_text):
        title = m.group(0).strip()
        positions.append((m.start(), title.lower().replace(" ", "_")[:40], title))
    positions.sort()

    # Build confirmed-section chunks and track their [start, end) spans.
    chunks = []
    covered_spans = []
    for i, (start, chunk_id, title) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else start + 3000
        chunks.append({
            "chunk_id": f"requity_{chunk_id}",
            "doc": "Racial Equity Plan",
            "unit_type": "section",
            "unit_id": title,
            "title": title,
            "text": full_text[start:end].strip(),
        })
        covered_spans.append((start, end))

    # Map each page to its character offset in full_text, so we can tell
    # which pages fall entirely outside every confirmed section's span.
    offset = 0
    page_offsets = []  # (page_num, page_text, start_offset, end_offset)
    for page_num, page_text in pages:
        start = offset
        end = start + len(page_text)
        page_offsets.append((page_num, page_text, start, end))
        offset = end + 1  # +1 for the "\n" join separator

    def is_covered(p_start, p_end):
        return any(c_start <= p_start and p_end <= c_end for c_start, c_end in covered_spans)

    uncovered_pages = [
        (page_num, page_text) for page_num, page_text, p_start, p_end in page_offsets
        if not is_covered(p_start, p_end)
    ]

    chunks += chunk_by_pages(uncovered_pages, "Racial Equity Plan_other")
    return chunks

def main():
    os.makedirs("data/chunks", exist_ok=True)

    all_chunks = []
    all_chunks += process_bvcp("data/processed/bvcp_full_text.txt")
    all_chunks += process_racial_equity_plan("data/processed/racial_equity_plan_full_text.txt")

    with open(CHUNKS_OUTPUT, "w") as f:
        json.dump(all_chunks, f, indent=2)

    by_type = {}
    for c in all_chunks:
        by_type[c["unit_type"]] = by_type.get(c["unit_type"], 0) + 1

    print(f"Wrote {len(all_chunks)} chunks to {CHUNKS_OUTPUT}")
    for unit_type, count in by_type.items():
        print(f"  {unit_type}: {count}")

if __name__ == "__main__":
    main()
