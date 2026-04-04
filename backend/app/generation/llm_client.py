"""
LLM client for answer generation.

Supports both OpenAI and Claude APIs. The provider is selected
via the LLM_PROVIDER env var ("openai" or "claude").
"""

from app.config import settings
from app.generation.prompts import SYSTEM_PROMPT, build_context_prompt


def _generate_openai(user_message: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content


def _generate_claude(user_message: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


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

    if settings.llm_provider == "claude":
        return _generate_claude(user_message)
    else:
        return _generate_openai(user_message)
