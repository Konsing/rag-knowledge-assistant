"""
LLM client for answer generation.

Supports both OpenAI and Claude APIs. The provider is selected
via the LLM_PROVIDER env var ("openai" or "claude").
"""

from app.config import settings
from app.generation.prompts import SYSTEM_PROMPT, build_context_prompt, remove_invalid_citations


def _generate_openai(user_message: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty response")
    return content


def _generate_claude(user_message: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    for block in response.content:
        if getattr(block, "type", None) == "text" and block.text:
            return block.text
    raise RuntimeError("Anthropic returned an empty response")


def generate_answer(question: str, chunks: list[dict]) -> str:
    """
    Generate a cited answer using the configured LLM provider.

    Args:
        question: The user's question
        chunks: Retrieved chunks with text, metadata, and score

    Returns:
        LLM answer with [1], [2] source citations
    """
    user_message = build_context_prompt(question, chunks)
    included_sources = user_message.count('<source id="')

    if settings.llm_provider == "claude":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        return remove_invalid_citations(_generate_claude(user_message), included_sources)
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return remove_invalid_citations(_generate_openai(user_message), included_sources)
