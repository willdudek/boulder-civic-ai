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

Usage:
    python3 extract_text.py <input_pdf> <output_txt>
"""
import sys
import re
import fitz  # PyMuPDF

WORD_COUNT_THRESHOLD = 10  # pages with fewer real words than this get flagged

def fix_letter_spacing(text):
    """Collapse decorative headings like 'A c k n o w l e d g e' back into words."""
    pattern = r'\b(?:[A-Za-z] ){3,}[A-Za-z]\b'
    return re.sub(pattern, lambda m: m.group(0).replace(' ', ''), text)

def extract(input_pdf, output_txt):
    doc = fitz.open(input_pdf)
    pages_text = []
    flagged_pages = []

    for i, page in enumerate(doc, start=1):
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
    if flagged_pages:
        print(f"Flagged as image-heavy / low-text (<{WORD_COUNT_THRESHOLD} words): {flagged_pages}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 extract_text.py <input_pdf> <output_txt>")
        sys.exit(1)
    extract(sys.argv[1], sys.argv[2])