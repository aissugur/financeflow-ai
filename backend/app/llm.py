"""Optional LLM synthesis layer.

The app NEVER requires this. If ANSWER_MODE=llm and a provider key is present,
we ask the model to answer strictly from the supplied context and to reply with
the abstain message when the context is insufficient. Any failure (missing
package, bad key, network error) falls back to extractive mode upstream.
"""
from typing import List, Optional

from . import config

SYSTEM_PROMPT = (
    "You are a careful financial-document assistant. Answer ONLY using the "
    "provided context excerpts. Do not invent numbers, dates, names, or facts. "
    "If the answer is not clearly supported by the context, reply with exactly: "
    f'"{config.ABSTAIN_MESSAGE}". Keep answers short and factual.'
)


def _build_user_prompt(question: str, contexts: List[str]) -> str:
    joined = "\n\n".join(f"[Excerpt {i + 1}]\n{c}" for i, c in enumerate(contexts))
    return f"CONTEXT:\n{joined}\n\nQUESTION: {question}\n\nANSWER:"


def synthesize(question: str, contexts: List[str]) -> Optional[str]:
    """Return an LLM answer string, or None to signal 'fall back to extractive'."""
    if config.ANSWER_MODE != "llm":
        return None
    try:
        if config.LLM_PROVIDER == "openai":
            return _openai(question, contexts)
        if config.LLM_PROVIDER == "anthropic":
            return _anthropic(question, contexts)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[llm] synthesis failed, falling back to extractive: {exc}")
        return None
    return None


def _openai(question: str, contexts: List[str]) -> Optional[str]:
    if not config.OPENAI_API_KEY:
        return None
    from openai import OpenAI  # lazy import

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(question, contexts)},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def _anthropic(question: str, contexts: List[str]) -> Optional[str]:
    if not config.ANTHROPIC_API_KEY:
        return None
    import anthropic  # lazy import

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=400,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": _build_user_prompt(question, contexts)},
        ],
    )
    parts = [block.text for block in resp.content if getattr(block, "type", "") == "text"]
    return "".join(parts).strip()
