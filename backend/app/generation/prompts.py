"""
Prompt templates for the generation layer.

Constructs the system prompt and user message that instruct Claude
to answer questions using only the retrieved context chunks,
with numbered source citations.
"""

SYSTEM_PROMPT = """You are a research assistant that answers questions based solely on the provided source documents.

Rules:
- ONLY use information from the provided sources to answer
- Cite sources using [1], [2], etc. notation inline with your answer
- If the sources don't contain enough information to answer, say "I don't have enough information in the provided sources to answer this question."
- Be concise but thorough — cover the key points from the sources
- Do not make up or infer information beyond what the sources state"""


def build_context_prompt(question: str, chunks: list[dict]) -> str:
    """
    Build the user message with numbered source chunks.

    Each chunk is labeled [1], [2], etc. with its metadata so Claude
    can cite them by number. The metadata (file, page, section) helps
    Claude understand what each source is about.

    Args:
        question: The user's question
        chunks: Retrieved chunks with text, metadata, and score

    Returns:
        Formatted prompt string for the user message
    """
    source_blocks = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        source_blocks.append(
            f"[{i}] Source: {meta['source_file']}, "
            f"Page {meta['page_number']}, "
            f"Section: {meta['section_title']}\n"
            f"{chunk['text']}"
        )

    sources_text = "\n\n---\n\n".join(source_blocks)

    return f"""Sources:

{sources_text}

---

Question: {question}"""
