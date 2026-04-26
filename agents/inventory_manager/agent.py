"""Inventory Manager Agent."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from uagents import Agent, Context

asyncio.set_event_loop(asyncio.new_event_loop())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agents.common.messages import InventoryAssessmentRequest, InventoryAssessmentResponse
from agents.inventory_manager.logic import run_inventory_assessment

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

agent = Agent(
    name="inventory_manager",
    seed="inventory_manager_seed_supplymind_2024",
    port=8005,
    network="testnet",
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(Path(__file__).resolve().parent / "README.md"),
)

AGENT_ADDRESS = agent.address


@agent.on_event("startup")
async def on_startup(ctx: Context) -> None:
    ctx.logger.info("Inventory Manager Agent ready. Address: %s", ctx.agent.address)


@agent.on_message(model=InventoryAssessmentRequest)
async def handle_request(
    ctx: Context, sender: str, msg: InventoryAssessmentRequest
) -> None:
    ctx.logger.info("InventoryAssessmentRequest from %s", sender)

    demand_decision = json.loads(msg.demand_decision_json)
    decision = await run_inventory_assessment(demand_decision, ctx)

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
    flags = outputs.get("flags", [])
    await ctx.send(
        sender,
        InventoryAssessmentResponse(
            summary=decision.summary,
            at_risk_count=outputs.get("at_risk_count", 0),
            excess_count=outputs.get("excess_count", 0),
            flags_json=json.dumps(flags),
            decision_json=decision.model_dump_json(),
        ),
    )


if __name__ == "__main__":
    agent.run()
