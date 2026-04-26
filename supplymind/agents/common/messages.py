"""Shared uAgent message models used across agents."""
import asyncio

# Python 3.14 removed implicit event loop creation; uagents requires one at import time.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from uagents import Model


class ForecastRequest(Model):
    requester: str = "coordinator"
    week: int = 47


class ForecastResponse(Model):
    """Demand Planning Agent → Coordinator: result of a ForecastRequest."""
    summary: str          # one-sentence headline (same as AgentDecision.summary)
    key_finding: str      # most critical stat, e.g. "SKU-4471 at 340% of baseline"
    decision_json: str    # full AgentDecision serialised as JSON string
