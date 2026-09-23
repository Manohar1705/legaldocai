"""
Step 8: LLM calls via Groq.

Groq's API is OpenAI-compatible (same request/response shape as
OpenAI's chat completions endpoint), so this is a plain HTTP POST — no
Groq-specific SDK needed. Model: openai/gpt-oss-120b (free tier,
131K context, fast on Groq's LPU hardware).
"""

import httpx

from app.core.config import settings

REQUEST_TIMEOUT_SECONDS = 30


class LLMError(Exception):
    pass


def call_llm(messages: list[dict], temperature: float = 0.2) -> str:
    """
    `messages` is a list of {"role": "system"|"user"|"assistant", "content": str},
    same shape the API expects directly — no translation needed.
    """
    if not settings.GROQ_API_KEY:
        raise LLMError(
            "GROQ_API_KEY is not set. Add it to backend/.env "
            "(get a free key at https://console.groq.com/keys)."
        )

    try:
        response = httpx.post(
            f"{settings.GROQ_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": settings.GROQ_MODEL,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise LLMError("The LLM took too long to respond. Try again.") from exc
    except httpx.HTTPStatusError as exc:
        raise LLMError(
            f"Groq API error ({exc.response.status_code}): {exc.response.text[:200]}"
        ) from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach Groq API: {exc}") from exc

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected response shape from Groq: {data}") from exc
