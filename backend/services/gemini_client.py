"""Google Gemini API client (carried over from the Script Desk template).

Used by the *Explain* stage (``services/explain.py``) to turn allocation
decisions into plain-language reasoning. Nothing else calls it, so the API
starts and works without a key (explanations then fall back to templates).

The key is read from the GEMINI_API_KEY environment variable, which
``main.py`` loads from ``backend/.env`` (git-ignored; see ``.env.example``).
The client is created lazily on first use.
"""
from __future__ import annotations

import os
from functools import lru_cache

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # the SDK costs ~45 MB of RAM: import it only when Gemini is actually called
    from google import genai

DEFAULT_MODEL = "gemini-flash-latest"


class GeminiNotConfiguredError(RuntimeError):
    """Raised when a Gemini call is attempted without GEMINI_API_KEY."""


def is_configured() -> bool:
    """True when a (non-empty) GEMINI_API_KEY is available."""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def model_name() -> str:
    """Model to call: GEMINI_MODEL if set, otherwise ``DEFAULT_MODEL``."""
    return os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """Return a shared Gemini client, creating it on first use."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and paste your key from https://aistudio.google.com/apikey."
        )
    from google import genai

    return genai.Client(api_key=api_key)


def generate_text(prompt: str, model: str | None = None) -> str:
    """Send a prompt to Gemini and return the generated text."""
    response = get_client().models.generate_content(
        model=model or model_name(),
        contents=prompt,
    )
    return response.text or ""
