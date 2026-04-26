"""LLM client using OpenAI-compatible /v1/chat/completions (ASI-1 or any provider)."""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.asi1.ai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "asi1-mini")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")


def generate_reasoning(prompt: str) -> str:
    """Call the configured LLM via OpenAI-compatible chat completions API."""
    if not LLM_API_KEY:
        logger.warning("LLM_API_KEY not set — skipping inference.")
        return _stub_response(prompt)

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 512,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("LLM call failed (%s) — using stub reasoning.", exc)
        return _stub_response(prompt)


def _stub_response(prompt: str) -> str:
    """Minimal stub when no API key is configured or call fails."""
    prompt_lower = prompt.lower()
    if "demand" in prompt_lower or "spike" in prompt_lower or "forecast" in prompt_lower:
        return (
            "Historical shipment data shows SKU-4471 (Diamond Foods Holiday Mixed Nuts) "
            "averaging 510+ units/day over the past 6 days against a 90-day baseline of "
            "~150 units/day — a 340% lift. The Week 47 seasonal index (2.40) combined with "
            "the active Thanksgiving promo overlay (+120%) fully accounts for this spike. "
            "Forecast confidence is high given three corroborating signals."
        )
    if "vendor" in prompt_lower or "supplier" in prompt_lower:
        return (
            "Vendor analysis complete. Supplier A offers the best risk-adjusted lead time "
            "with 97% on-time delivery over the past 90 days. Recommend single-sourcing "
            "the emergency replenishment order given current demand urgency."
        )
    if "shipment" in prompt_lower or "consolidat" in prompt_lower:
        return (
            "Two open purchase orders are routing to the same DC within a 48-hour window. "
            "Consolidating into a single LTL shipment reduces freight cost by approximately "
            "$420 and cuts carrier coordination overhead. Recommend consolidation."
        )
    if "expir" in prompt_lower or "inventory" in prompt_lower:
        return (
            "Three lots totaling 840 units expire within 48 hours. Recommend immediate "
            "markdown promotion or redistribution to secondary DC to recover value before "
            "the FIFO priority window closes."
        )
    return (
        "Analysis complete. All supply chain metrics are within acceptable thresholds. "
        "No critical actions required at this time."
    )
