"""
Boulder Civic AI — extract_text.py
General-purpose PDF -> plain text extraction for the project's corpus.

Handles known layout quirks found so far:
  - Multi-column pages reading out of order (PyMuPDF's default handles
    this correctly for documents seen so far)
  - Decorative wide-letter-spaced headings extracting as single
    space-separated letters (fixed via post-processing regex)
  - Image-heavy pages (little to no real extractable text) are detected
    automatically and flagged with a placeholder rather than silently
    losing that content with no trace — no manual page inspection required
  - Decorative pages with spatially-arranged text (e.g. word-cloud style
    cover art) can extract as scrambled, out-of-order characters that no
    regex can fix, since the letters themselves come out of order, not
    just the spacing. These must be explicitly skipped per document via
    the optional skip_pages argument -- this is NOT hardcoded, since it's
    specific to individual documents' cover art, not a general pattern.

Usage:
    python3 extract_text.py <input_pdf> <output_txt> [skip_pages]

    skip_pages: optional comma-separated 1-indexed page numbers to skip
    entirely (e.g. "1" or "1,2"). Defaults to none skipped -- every
    document is extracted in full unless you explicitly flag pages to
    skip for that specific document.
"""
import sys
import re
import fitz  # PyMuPDF

WORD_COUNT_THRESHOLD = 10  # pages with fewer real words than this get flagged

def fix_letter_spacing(text):
    """Collapse decorative headings like 'A c k n o w l e d g e' back into words."""
    pattern = r'\b(?:[A-Za-z] ){3,}[A-Za-z]\b'
    return re.sub(pattern, lambda m: m.group(0).replace(' ', ''), text)

def extract(input_pdf, output_txt, skip_pages=None):
    skip_pages = skip_pages or set()
    doc = fitz.open(input_pdf)
    pages_text = []
    flagged_pages = []

    for i, page in enumerate(doc, start=1):
        if i in skip_pages:
            pages_text.append(
                f"--- Page {i} ---\n"
                f"[Page skipped -- decorative content with scrambled/unfixable "
                f"text extraction. Check the source PDF directly if needed.]\n"
            )
            continue

        text = page.get_text("text")
        word_count = len(text.strip().split())

        if word_count < WORD_COUNT_THRESHOLD:
            pages_text.append(
                f"--- Page {i} ---\n"
                f"[This page has very little extractable text ({word_count} words) "
                f"— may be primarily an image, map, or graphic. If this section "
                f"matters, check the source PDF directly for this page's visual "
                f"content.]\n"
            )
            flagged_pages.append(i)
            continue

        pages_text.append(f"--- Page {i} ---\n{text}\n")

    combined = "\n".join(pages_text)
    combined = fix_letter_spacing(combined)

    with open(output_txt, "w") as f:
        f.write(combined)

    print(f"Extracted {len(doc)} pages, {len(combined)} characters "
          f"(~{len(combined)//4} tokens) to {output_txt}")
    if skip_pages:
        print(f"Skipped (explicit, per-document): {sorted(skip_pages)}")
    if flagged_pages:
        print(f"Flagged as image-heavy / low-text (<{WORD_COUNT_THRESHOLD} words): {flagged_pages}")

if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print("Usage: python3 extract_text.py <input_pdf> <output_txt> [skip_pages]")
        sys.exit(1)

    input_pdf, output_txt = sys.argv[1], sys.argv[2]
    skip_pages = set()
    if len(sys.argv) == 4:
        skip_pages = {int(p) for p in sys.argv[3].split(",")}

    extract(input_pdf, output_txt, skip_pages)
