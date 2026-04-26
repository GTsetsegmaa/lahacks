"""LLM client wrapping local Ollama (Gemma). Falls back to a stub if unreachable."""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("LLM_MODEL", "gemma3")

_STUB = (
    "Historical shipment data shows SKU-4471 (Diamond Foods Holiday Mixed Nuts) "
    "averaging 510+ units/day over the past 6 days against a 90-day baseline of "
    "~150 units/day — a 340% lift. The Week 47 seasonal index (2.40) combined with "
    "the active Thanksgiving promo overlay (+120%) fully accounts for this spike. "
    "Forecast confidence is high given three corroborating signals."
)


def generate_reasoning(prompt: str) -> str:
    """Call Ollama/Gemma; return stub if Ollama is unreachable."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ollama unavailable (%s) — using stub reasoning.", exc)
        return _STUB
