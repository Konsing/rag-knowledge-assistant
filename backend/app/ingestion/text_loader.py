"""
Plain text and markdown file loader.

Reads .txt and .md files, returning a single-page result compatible
with the chunker interface (same shape as pdf_loader output).
"""


def extract_text_from_file(file_path: str) -> list[dict]:
    """
    Read a plain text or markdown file.

    Returns:
        List of {page_number, text} dicts (single entry for text files).
        Empty list if file has no meaningful content.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    if len(text.strip()) < 50:
        return []

    return [{"page_number": 1, "text": text}]
