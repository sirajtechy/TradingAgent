"""
llm_summary.py — Post-score LLM narrative helper.

Rules (matching FUNDAMENTAL_AGENT_SPEC.md philosophy):
  - NEVER mutates deterministic scores.
  - Called AFTER all scoring is complete.
  - Returns structured JSON: { sentiment, bullets, confidence }.
  - Cache keyed by (agent_id, as_of_date, content_hash).
  - Disabled with LLM_ENABLED=false or --llm off at CLI.

Usage::

    from agents._shared.llm_summary import generate_summary, is_llm_enabled

    if is_llm_enabled():
        result = generate_summary(
            agent_id="news",
            as_of_date="2026-06-01",
            context="... headline text ...",
            instruction="Classify sentiment and produce 2-3 bullet points.",
        )
        # result = {"sentiment": "positive", "bullets": [...], "confidence": "medium"}
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CACHE_DIR = _PROJECT_ROOT / "data" / "output" / "llm_cache"


def is_llm_enabled() -> bool:
    provider = os.getenv("LLM_PROVIDER", "deterministic").strip().lower()
    if provider in ("off", "none", "deterministic"):
        return False
    val = os.getenv("LLM_ENABLED", "false").strip().lower()
    return val in ("true", "1", "yes")


def _cache_key(agent_id: str, as_of_date: str, content_hash: str) -> str:
    return f"{agent_id}_{as_of_date}_{content_hash}"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _read_cache(key: str) -> Optional[Dict[str, Any]]:
    path = _CACHE_DIR / f"{key}.json"
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _write_cache(key: str, data: Dict[str, Any]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _CACHE_DIR / f"{key}.json"
    try:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    except OSError as exc:
        logger.warning("LLM cache write failed: %s", exc)


def _get_model() -> str:
    return os.getenv("LLM_MODEL", "gpt-4o-mini")


def _call_openai(model: str, system: str, user: str) -> str:
    """Call OpenAI-compatible chat completion API."""
    import requests

    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set — cannot call LLM")

    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0.3,
            "max_tokens": 300,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


_SYSTEM_PROMPT = (
    "You are a financial market analyst. Given context about a stock or market, "
    "produce a JSON object with exactly these keys:\n"
    '  "sentiment": one of "positive", "neutral", "negative"\n'
    '  "bullets": array of 2-3 short bullet strings (start each with "•")\n'
    '  "confidence": one of "high", "medium", "low"\n'
    "Do not include any other keys. Be concise."
)


def generate_summary(
    *,
    agent_id: str,
    as_of_date: str,
    context: str,
    instruction: str = "",
) -> Dict[str, Any]:
    """
    Generate a post-score LLM narrative.

    Returns dict with keys: sentiment, bullets, confidence.
    Returns a safe fallback on any failure.
    """
    ch = _content_hash(context)
    cache_key = _cache_key(agent_id, as_of_date, ch)

    cached = _read_cache(cache_key)
    if cached is not None:
        logger.debug("LLM cache hit: %s", cache_key)
        return cached

    model = _get_model()
    user_msg = f"{instruction}\n\nContext:\n{context}" if instruction else context

    try:
        raw = _call_openai(model, _SYSTEM_PROMPT, user_msg)
        result = json.loads(raw)
        result.setdefault("sentiment", "neutral")
        result.setdefault("bullets", [])
        result.setdefault("confidence", "medium")
    except Exception as exc:
        logger.warning("LLM call failed for %s: %s — using fallback", agent_id, exc)
        result = {
            "sentiment": "neutral",
            "bullets": [f"• LLM summary unavailable ({type(exc).__name__})"],
            "confidence": "low",
        }

    _write_cache(cache_key, result)
    return result


def generate_summary_safe(
    *,
    agent_id: str,
    as_of_date: str,
    context: str,
    instruction: str = "",
) -> Optional[Dict[str, Any]]:
    """Like generate_summary but returns None when LLM is disabled."""
    if not is_llm_enabled():
        return None
    return generate_summary(
        agent_id=agent_id,
        as_of_date=as_of_date,
        context=context,
        instruction=instruction,
    )
