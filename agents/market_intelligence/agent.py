"""Market Intelligence Agent."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx
from uagents import Agent, Context

asyncio.set_event_loop(asyncio.new_event_loop())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agents.common.messages import MarketIntelRequest, MarketIntelResponse
from agents.market_intelligence.logic import run_market_intelligence

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

agent = Agent(
    name="market_intelligence",
    seed="market_intelligence_seed_supplymind_2024",
    port=8004,
    endpoint=["http://localhost:8004/submit"],
)

AGENT_ADDRESS = agent.address


@agent.on_event("startup")
async def on_startup(ctx: Context) -> None:
    ctx.logger.info("Market Intelligence Agent ready. Address: %s", ctx.agent.address)


@agent.on_message(model=MarketIntelRequest)
async def handle_request(ctx: Context, sender: str, msg: MarketIntelRequest) -> None:
    ctx.logger.info("MarketIntelRequest from %s", sender)

    decision = run_market_intelligence()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{BACKEND_URL}/api/decisions",
                content=decision.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            ctx.logger.error("Failed to post to backend: %s", exc)

    outputs = decision.outputs
    await ctx.send(sender, MarketIntelResponse(
        summary=decision.summary,
        has_fuel_spike=bool(outputs.get("has_fuel_spike")),
        affected_lanes=outputs.get("affected_lanes", []),
        signals_json=decision.model_dump_json(),   # full decision as JSON
        decision_json=decision.model_dump_json(),
    ))


if __name__ == "__main__":
    agent.run()
