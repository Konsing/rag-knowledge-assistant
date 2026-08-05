"""
Section-aware text chunker with overlap.

Splits document text into chunks that respect section boundaries,
with configurable size and overlap. Falls back to paragraph/sentence
splitting when section headers aren't detected.
"""

import re
import hashlib

from app.config import settings

# Patterns that indicate section headers in academic papers.
# Ordered by specificity — we try the most reliable patterns first.
SECTION_PATTERNS = [
    # Numbered sections: "1 Introduction", "2.1 Methods", "3. Results"
    # Must start with a small number (1-9) to avoid matching table data like "57.84 Tencent"
    r"\n[1-9]\.?\d*\.?\s+[A-Z][A-Za-z ]{2,40}\n",
    # ALL-CAPS headers: "INTRODUCTION", "RELATED WORK"
    r"\n[A-Z][A-Z ]{2,30}\n",
]

# Minimum number of sections to consider detection successful
MIN_SECTIONS = 3
# Maximum — if we find more than this, the pattern is matching noise
MAX_SECTIONS = 20
# Sections shorter than this (chars) are likely false positives
MIN_SECTION_LENGTH = 100

# Patterns that indicate the start of a references/bibliography section
REFERENCES_PATTERNS = [
    r"\n(?:References|REFERENCES|Bibliography|BIBLIOGRAPHY)\s*\n",
]


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1 token per 4 characters for English text."""
    return len(text) // 4


def _strip_references(text: str) -> str:
    """
    Remove the references/bibliography section from the end of a paper.
    This section pollutes retrieval with noise (author names, paper titles).
    """
    for pattern in REFERENCES_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return text[: match.start()]
    return text


def _detect_sections(text: str) -> list[dict]:
    """
    Split text into sections based on detected headers.

    Tries patterns in order of specificity. Accepts the first pattern
    that produces a reasonable number of sections (3-20). Falls back to
    treating the entire document as one section.

    Returns:
        List of dicts with keys: title, text
    """
    for pattern in SECTION_PATTERNS:
        headers = list(re.finditer(pattern, text))
        if MIN_SECTIONS <= len(headers) <= MAX_SECTIONS:
            sections = _headers_to_sections(headers, text)
            sections = _merge_short_sections(sections)
            if len(sections) >= 2:
                return sections

    # Fallback: no reliable sections detected — treat as one block
    return [{"title": "Full Document", "text": text, "start": 0, "end": len(text)}]


def _headers_to_sections(headers: list, text: str) -> list[dict]:
    """Convert regex header matches into section dicts."""
    sections = []
    if headers and headers[0].start() > 0:
        preamble = text[:headers[0].start()].strip()
        if preamble:
            preamble_start = text.find(preamble)
            sections.append({
                "title": "Preamble",
                "text": preamble,
                "start": preamble_start,
                "end": preamble_start + len(preamble),
            })

    for i, header in enumerate(headers):
        title = header.group().strip()
        start = header.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        section_text = text[start:end].strip()

        if section_text:
            text_start = text.find(section_text, start, end)
            sections.append({
                "title": title,
                "text": section_text,
                "start": text_start,
                "end": text_start + len(section_text),
            })

    return sections


def _merge_short_sections(sections: list[dict]) -> list[dict]:
    """Merge short sections into a neighbor instead of discarding their content."""
    merged: list[dict] = []
    for section in sections:
        if len(section["text"]) >= MIN_SECTION_LENGTH or not merged:
            merged.append(section.copy())
            continue

        previous = merged[-1]
        previous["text"] = f"{previous['text']}\n\n{section['title']}\n{section['text']}"
        previous["end"] = section["end"]

    if len(merged) > 1 and len(merged[0]["text"]) < MIN_SECTION_LENGTH:
        first = merged.pop(0)
        merged[0]["text"] = f"{first['text']}\n\n{merged[0]['text']}"
        merged[0]["start"] = first["start"]
    return merged


def _split_into_chunks(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """
    Split text into chunks of approximately chunk_size tokens with overlap.

    Strategy:
    1. Split into paragraphs (double newline)
    2. Accumulate paragraphs until chunk_size is reached
    3. When a chunk is full, start the next chunk with overlap from the end
       of the previous chunk
    """
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk_parts: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _estimate_tokens(para)

        # If a single paragraph exceeds chunk_size, split it by sentences
        if para_tokens > chunk_size:
            # Flush current chunk first
            if current_chunk_parts:
                chunks.append("\n\n".join(current_chunk_parts))
                current_chunk_parts = []
                current_tokens = 0

            # Split long paragraph by sentences
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                sent_tokens = _estimate_tokens(sentence)
                if sent_tokens > chunk_size:
                    if current_chunk_parts:
                        chunks.append(" ".join(current_chunk_parts))
                        current_chunk_parts = []
                        current_tokens = 0
                    max_chars = chunk_size * 4
                    overlap_chars = chunk_overlap * 4
                    step = max(1, max_chars - overlap_chars)
                    for start in range(0, len(sentence), step):
                        piece = sentence[start:start + max_chars]
                        if piece:
                            chunks.append(piece)
                        if start + max_chars >= len(sentence):
                            break
                    continue
                if current_tokens + sent_tokens > chunk_size and current_chunk_parts:
                    chunks.append(" ".join(current_chunk_parts))
                    # Keep overlap worth of text
                    overlap_text = " ".join(current_chunk_parts)
                    overlap_start = max(0, len(overlap_text) - chunk_overlap * 4)
                    current_chunk_parts = [overlap_text[overlap_start:]]
                    current_tokens = _estimate_tokens(current_chunk_parts[0])
                current_chunk_parts.append(sentence)
                current_tokens += sent_tokens
            continue

        # Check if adding this paragraph would exceed the limit
        if current_tokens + para_tokens > chunk_size and current_chunk_parts:
            chunk_text = "\n\n".join(current_chunk_parts)
            chunks.append(chunk_text)

            # Create overlap: take the tail of the current chunk
            overlap_start = max(0, len(chunk_text) - chunk_overlap * 4)
            overlap_text = chunk_text[overlap_start:]
            current_chunk_parts = [overlap_text]
            current_tokens = _estimate_tokens(overlap_text)

        current_chunk_parts.append(para)
        current_tokens += para_tokens

    # Don't forget the last chunk
    if current_chunk_parts:
        chunks.append("\n\n".join(current_chunk_parts))

    return chunks


# Markdown heading patterns for non-academic documents
MARKDOWN_HEADING_PATTERN = r"(?m)^#{1,3}\s+.+$"


def _detect_markdown_sections(text: str) -> list[dict]:
    """
    Detect sections from markdown headings (# Title, ## Subtitle, etc.).

    Falls back to treating the entire document as one section
    if fewer than 2 headings are found.
    """
    headers = list(re.finditer(MARKDOWN_HEADING_PATTERN, text))
    if len(headers) >= 2:
        sections = _headers_to_sections(headers, text)
        sections = _merge_short_sections(sections)
        if len(sections) >= 2:
            return sections

    return [{"title": "Full Document", "text": text, "start": 0, "end": len(text)}]


def _document_id(source_file: str, text: str) -> str:
    """Create a stable ID so re-ingesting identical content is idempotent."""
    digest = hashlib.sha256(f"{source_file}\0{text}".encode("utf-8")).hexdigest()
    return digest[:16]


def _validate_chunk_parameters(chunk_size: int, chunk_overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")


def chunk_plain_document(
    pages: list[dict],
    source_file: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """
    Chunk a non-academic document (text, markdown, web page).

    Unlike chunk_document(), this skips reference stripping and academic
    section detection. Uses markdown heading detection if available,
    otherwise falls back to paragraph-based splitting.

    Args:
        pages: List of {page_number, text} dicts
        source_file: Source identifier (filename or URL)
        chunk_size: Target chunk size in tokens (default from config)
        chunk_overlap: Overlap between chunks in tokens (default from config)

    Returns:
        List of dicts with keys: text, metadata
    """
    chunk_size = settings.chunk_size if chunk_size is None else chunk_size
    chunk_overlap = settings.chunk_overlap if chunk_overlap is None else chunk_overlap
    _validate_chunk_parameters(chunk_size, chunk_overlap)

    full_text = "\n".join(p["text"] for p in pages)
    sections = _detect_markdown_sections(full_text)

    doc_id = _document_id(source_file, full_text)
    all_chunks = []
    chunk_index = 0

    for section in sections:
        section_chunks = _split_into_chunks(
            section["text"], chunk_size, chunk_overlap
        )

        for chunk_text in section_chunks:
            if len(chunk_text.strip()) < 50:
                continue

            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source_file": source_file,
                    "page_number": 1,
                    "section_title": section["title"],
                    "chunk_index": chunk_index,
                    "doc_id": doc_id,
                },
            })
            chunk_index += 1

    return all_chunks


def chunk_document(
    pages: list[dict],
    source_file: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """
    Chunk a document into pieces suitable for embedding.

    Takes the output of pdf_loader.extract_text_from_pdf() and produces
    chunks with full metadata for citation tracking.

    Args:
        pages: List of {page_number, text} dicts from PDF extraction
        source_file: Filename of the source PDF
        chunk_size: Target chunk size in tokens (default from config)
        chunk_overlap: Overlap between chunks in tokens (default from config)

    Returns:
        List of dicts with keys: text, metadata (ChunkMetadata fields)
    """
    chunk_size = settings.chunk_size if chunk_size is None else chunk_size
    chunk_overlap = settings.chunk_overlap if chunk_overlap is None else chunk_overlap
    _validate_chunk_parameters(chunk_size, chunk_overlap)

    # Combine all pages into one text, tracking page boundaries
    full_text = ""
    page_boundaries: list[tuple[int, int, int]] = []  # (start, end, page_num)

    for page in pages:
        start = len(full_text)
        full_text += page["text"] + "\n"
        page_boundaries.append((start, len(full_text), page["page_number"]))

    # Strip references section before chunking
    full_text = _strip_references(full_text)

    # Detect sections
    sections = _detect_sections(full_text)

    # Generate a unique document ID
    doc_id = _document_id(source_file, full_text)

    # Chunk each section, then assign page numbers from boundaries
    all_chunks = []
    chunk_index = 0

    for section in sections:
        section_chunks = _split_into_chunks(
            section["text"], chunk_size, chunk_overlap
        )

        search_from = section["start"]
        for chunk_text in section_chunks:
            # Find which page this chunk starts on by matching position
            # in the original text
            lookup_start = max(section["start"], search_from - chunk_overlap * 4)
            chunk_start = full_text.find(chunk_text[:100], lookup_start, section["end"])
            page_num = 1  # default
            for start, end, pnum in page_boundaries:
                if start <= chunk_start < end:
                    page_num = pnum
                    break
            if chunk_start >= 0:
                search_from = max(
                    chunk_start + 1,
                    chunk_start + len(chunk_text) - chunk_overlap * 4,
                )

            # Skip tiny chunks — they have no useful content for retrieval
            if len(chunk_text.strip()) < 50:
                continue

            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source_file": source_file,
                    "page_number": page_num,
                    "section_title": section["title"],
                    "chunk_index": chunk_index,
                    "doc_id": doc_id,
                },
            })
            chunk_index += 1

    return all_chunks
