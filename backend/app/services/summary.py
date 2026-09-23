"""
Step 9: document summary.

Unlike chat (Step 8), this doesn't retrieve chunks — a summary needs the
whole document, not just the parts relevant to one question. It reuses
the same call_llm() from Step 8, just with a different prompt and the
full extracted_text as input instead of retrieved chunks.
"""

from app.services.llm import call_llm

# openai/gpt-oss-120b has a 131K-token context window, but extremely long
# documents (100+ pages) could still blow past that once the prompt and
# instructions are added. Truncating defensively here means a huge
# document degrades to "summarized from the first ~40K chars" instead of
# the request failing outright with a 502 from Groq.
MAX_INPUT_CHARS = 40_000

SYSTEM_PROMPT = """You are a legal document assistant helping a non-lawyer \
understand a contract. Summarize the document below in plain, simple \
language. Structure your summary as:

1. A short overview (2-3 sentences) of what kind of document this is and \
what it covers.
2. Key terms and obligations, as a bullet list — payment terms, \
deadlines, responsibilities of each party.
3. Anything a non-lawyer should pay particular attention to (penalties, \
auto-renewal clauses, unusual terms).

Base the summary ONLY on the text provided — do not guess or add \
information that isn't there."""


def generate_summary(extracted_text: str) -> str:
    text = extracted_text.strip()
    truncated = len(text) > MAX_INPUT_CHARS
    if truncated:
        text = text[:MAX_INPUT_CHARS]

    user_content = text
    if truncated:
        user_content += (
            "\n\n[Note: this document was truncated for length — the "
            "summary above covers only the beginning of the document.]"
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    return call_llm(messages, temperature=0.2)
