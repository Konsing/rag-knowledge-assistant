from app.ingestion.chunker import (
    _detect_markdown_sections,
    _detect_sections,
    _estimate_tokens,
    _split_into_chunks,
    chunk_document,
    chunk_plain_document,
)


def test_section_detection_preserves_preamble():
    preamble = "Abstract " + "important finding " * 20
    body = "".join(
        f"\n{i} {title}\n" + f"{title} content. " * 30
        for i, title in enumerate(("Introduction", "Methods", "Results"), 1)
    )
    sections = _detect_sections(preamble + body)

    assert sections[0]["title"] == "Preamble"
    assert "important finding" in sections[0]["text"]


def test_single_long_sentence_respects_hard_chunk_limit():
    chunks = _split_into_chunks("x" * 2_400 + ".", chunk_size=100, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(_estimate_tokens(chunk) <= 100 for chunk in chunks)


def test_markdown_heading_at_first_line_is_detected():
    text = "# First\n" + "alpha " * 30 + "\n\n## Second\n" + "beta " * 30

    assert [section["title"] for section in _detect_markdown_sections(text)] == [
        "# First",
        "## Second",
    ]


def test_identical_document_has_stable_id():
    pages = [{"page_number": 1, "text": "A useful paragraph. " * 20}]

    first = chunk_plain_document(pages, "notes.txt")
    second = chunk_plain_document(pages, "notes.txt")

    assert first[0]["metadata"]["doc_id"] == second[0]["metadata"]["doc_id"]


def test_invalid_overlap_is_rejected():
    pages = [{"page_number": 1, "text": "A useful paragraph. " * 20}]

    try:
        chunk_document(pages, "paper.pdf", chunk_size=100, chunk_overlap=100)
    except ValueError as exc:
        assert "chunk_overlap" in str(exc)
    else:
        raise AssertionError("Expected invalid overlap to be rejected")
