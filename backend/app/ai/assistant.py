import logging
import os
import threading
from collections import OrderedDict

import requests

from app.ai.offline import explain_offline
from app.ai.fixes import MAX_FIX_SOURCE_CHARS, parse_model_json
from app.ai.prompts import (
    LEVELS, SYSTEM_PROMPTS, SYSTEM_PROMPT_BEGINNER_WITH_FIX,
    build_fix_user_prompt, build_user_prompt,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"
CONTEXT_LINES = 3        # lines shown before/after the error line
MAX_EXCERPT_LINES = 40   # cap for errors with no usable line number
CACHE_SIZE = 256

_cache = OrderedDict()
_cache_lock = threading.Lock()


def clear_cache():
    with _cache_lock:
        _cache.clear()


def build_excerpt(source_code, line, context=CONTEXT_LINES):
    """Numbered excerpt around `line`; the error line is marked with '>'."""
    lines = source_code.splitlines() or [""]
    if line and 1 <= line <= len(lines):
        start, end = max(1, line - context), min(len(lines), line + context)
    else:
        start, end = 1, min(len(lines), MAX_EXCERPT_LINES)
    width = len(str(end))
    return "\n".join(
        f"{'>' if n == line else ' '} {str(n).rjust(width)} | {lines[n - 1]}"
        for n in range(start, end + 1)
    )


class AIAssistant:
    """Explains compiler errors at two levels: "beginner" and "simple"."""

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.api_url = os.environ.get("LUMEN_AI_API_URL", DEFAULT_API_URL)
        self.model = os.environ.get("LUMEN_AI_MODEL", DEFAULT_MODEL)
        self.timeout = float(os.environ.get("LUMEN_AI_TIMEOUT", "12"))

    def explain(self, source_code, error_message, line=0, level="beginner", previous=None):
        """Return {"explanation": str, "source": "ai" | "offline", "level": str}."""
        if level not in LEVELS:
            raise ValueError(f"level must be one of {LEVELS}")

        if self.api_key:
            excerpt = build_excerpt(source_code, line)
            key = (self.model, level, error_message, excerpt, previous or "")
            with _cache_lock:
                cached = _cache.get(key)
                if cached is not None:
                    _cache.move_to_end(key)
                    return {"explanation": cached, "source": "ai", "level": level}

            text = self._ask_model(level, excerpt, error_message, line, previous)
            if text:
                with _cache_lock:
                    _cache[key] = text
                    while len(_cache) > CACHE_SIZE:
                        _cache.popitem(last=False)
                return {"explanation": text, "source": "ai", "level": level}

        return {"explanation": explain_offline(error_message, level), "source": "offline", "level": level}

    def explain_error(self, source_code, error_message, line=0, level="beginner"):
        """Convenience wrapper that returns only the explanation text."""
        return self.explain(source_code, error_message, line, level)["explanation"]

    def explain_with_fix(self, source_code, error_message, line=0,
                         rejected_fix=None, rejection_reason=None, remaining_errors=None):
        """Beginner-level explanation plus a proposed complete fixed program.

        Returns {"explanation", "fixed_code" (or None), "source", "level"}.
        The fix is only a *candidate*: the caller must verify it by compiling
        it (see app.services.fix_verifier) before showing it as verified."""
        if self.api_key and len(source_code) <= MAX_FIX_SOURCE_CHARS:
            key = ("fix", self.model, error_message, source_code, line,
                   rejected_fix or "", rejection_reason or "", tuple(remaining_errors or ()))
            with _cache_lock:
                cached = _cache.get(key)
                if cached is not None:
                    _cache.move_to_end(key)
                    return {"explanation": cached[0], "fixed_code": cached[1], "source": "ai", "level": "beginner"}

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_BEGINNER_WITH_FIX},
                {"role": "user", "content": build_fix_user_prompt(
                    source_code, error_message, line, rejected_fix, rejection_reason, remaining_errors)},
            ]
            extra = {"response_format": {"type": "json_object"}} if "api.openai.com" in self.api_url else {}
            text = self._chat(messages, max_tokens=1200, **extra)
            explanation, fixed_code = parse_model_json(text)
            if explanation:
                with _cache_lock:
                    _cache[key] = (explanation, fixed_code)
                    while len(_cache) > CACHE_SIZE:
                        _cache.popitem(last=False)
                return {"explanation": explanation, "fixed_code": fixed_code, "source": "ai", "level": "beginner"}

        # Offline / failure / program too large to echo: explanation only.
        fallback = self.explain(source_code, error_message, line, "beginner")
        return {"explanation": fallback["explanation"], "fixed_code": None,
                "source": fallback["source"], "level": "beginner"}

    def _ask_model(self, level, excerpt, error_message, line, previous):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPTS[level]},
            {"role": "user", "content": build_user_prompt(level, excerpt, error_message, line, previous)},
        ]
        return self._chat(messages, max_tokens=350)

    def _chat(self, messages, max_tokens, **extra_payload):
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
            **extra_payload,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout)
            if response.status_code != 200:
                logger.warning("AI service returned status %s", response.status_code)
                return None
            text = response.json()["choices"][0]["message"]["content"]
            return text.strip() or None
        except Exception as exc:  # network error, bad JSON, unexpected shape...
            logger.warning("AI service unavailable: %s", exc)
            return None
