"""Optional LLM synthesis layer for "thinking" mode.

The app NEVER requires this. When the user picks Thinking mode AND a provider key
is configured, we ask the model to reason and answer strictly from the supplied
context, replying with the abstain message when the context is insufficient.
Any failure (missing package, bad key, network error) returns None so the caller
falls back to the extractive Fast engine.

Anthropic path uses adaptive thinking (`thinking={"type": "adaptive"}`) — the
correct extended-thinking shape for current Claude models — so it genuinely
"thinks on the fly". Note: temperature must NOT be sent alongside adaptive
thinking on current models.
"""
import logging
from typing import List, Optional

from . import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a careful financial-document assistant. Answer ONLY using the "
    "provided context excerpts. Reason step by step, then give a short, factual "
    "answer. Never invent numbers, dates, names, or company names. If the answer "
    "is not clearly supported by the context, reply with exactly: "
    f'"{config.ABSTAIN_MESSAGE}".'
)


def _build_user_prompt(question: str, contexts: List[str]) -> str:
    joined = "\n\n".join(f"[Excerpt {i + 1}]\n{c}" for i, c in enumerate(contexts))
    return f"CONTEXT:\n{joined}\n\nQUESTION: {question}\n\nANSWER:"


def synthesize(question: str, contexts: List[str]) -> Optional[str]:
    """Return an LLM answer string, or None to signal 'fall back to Fast'."""
    try:
        if config.LLM_PROVIDER == "openai":
            return _openai(question, contexts)
        if config.LLM_PROVIDER == "anthropic":
            return _anthropic(question, contexts)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("LLM synthesis failed, falling back to Fast: %s", exc)
        return None
    return None


def _anthropic(question: str, contexts: List[str]) -> Optional[str]:
    if not config.ANTHROPIC_API_KEY:
        return None
    import anthropic  # lazy import

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=2048,  # generous: must cover adaptive thinking + the answer
        thinking={"type": "adaptive"},  # reason on the fly (no temperature with this)
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(question, contexts)}],
    )
    # Take only the visible text blocks; thinking blocks are skipped.
    parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    return "".join(parts).strip() or None


def _openai(question: str, contexts: List[str]) -> Optional[str]:
    if not config.OPENAI_API_KEY:
        return None
    from openai import OpenAI  # lazy import

    # base_url lets us target any OpenAI-compatible provider (incl. free tiers).
    kwargs = {"api_key": config.OPENAI_API_KEY}
    if config.OPENAI_BASE_URL:
        kwargs["base_url"] = config.OPENAI_BASE_URL
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(question, contexts)},
        ],
    )
    return (resp.choices[0].message.content or "").strip() or None
