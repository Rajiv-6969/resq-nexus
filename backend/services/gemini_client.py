"""Google Gemini API client (carried over from the Script Desk template).

ResQ Nexus will use Gemini in the *Explain* stage to turn allocation
decisions into plain-language reasoning. The Assess and Prioritise stages
do not call it, so the API starts and works without a key.

The key is read from the GEMINI_API_KEY environment variable, which
``main.py`` loads from ``backend/.env`` (git-ignored; see ``.env.example``).
The client is created lazily on first use.
"""
from __future__ import annotations

import os
from functools import lru_cache

from google import genai

DEFAULT_MODEL = "gemini-flash-latest"


class GeminiNotConfiguredError(RuntimeError):
    """Raised when a Gemini call is attempted without GEMINI_API_KEY."""


def is_configured() -> bool:
    """True when a (non-empty) GEMINI_API_KEY is available."""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """Return a shared Gemini client, creating it on first use."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and paste your key from https://aistudio.google.com/apikey."
        )
    return genai.Client(api_key=api_key)


def generate_text(prompt: str, model: str | None = None) -> str:
    """Send a prompt to Gemini and return the generated text."""
    response = get_client().models.generate_content(
        model=model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
        contents=prompt,
    )
    return response.text
