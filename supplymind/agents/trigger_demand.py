#!/usr/bin/env python3
"""
Send a ForecastRequest to the running Demand Planning Agent.

Usage (demand planning agent must already be running):
  python agents/trigger_demand.py

If uAgent local discovery fails (no Agentverse), use the HTTP fallback:
  curl -X POST http://localhost:8000/api/trigger/demand
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from uagents import Agent, Context

# Python 3.14 removed implicit event loop creation; uagents requires one at init time.
asyncio.set_event_loop(asyncio.new_event_loop())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.common.messages import ForecastRequest
from agents.demand_planning.agent import AGENT_ADDRESS  # derived from fixed seed

print(f"Sending ForecastRequest to demand planning agent: {AGENT_ADDRESS}")

sender = Agent(
    name="demand_trigger",
    seed="trigger_seed_supplymind_2024",
    port=8002,
    endpoint=["http://localhost:8002/submit"],
)


@sender.on_event("startup")
async def fire(ctx: Context) -> None:
    await ctx.send(AGENT_ADDRESS, ForecastRequest(requester="trigger", week=47))
    ctx.logger.info("ForecastRequest sent. Watch the demand agent logs and dashboard.")


if __name__ == "__main__":
    sender.run()
