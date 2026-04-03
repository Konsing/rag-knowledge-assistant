"""
PDF text extraction using PyMuPDF.

Extracts text from each page of a PDF, preserving page numbers
for downstream citation tracking.
"""

import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text from a PDF file, returning per-page results.

    Returns:
        List of dicts with keys: page_number (1-indexed), text
    """
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        # Skip pages with negligible text (e.g., figures-only pages)
        if len(text.strip()) < 50:
            continue

        pages.append({
            "page_number": page_num + 1,  # 1-indexed for human readability
            "text": text,
        })

    doc.close()
    return pages
