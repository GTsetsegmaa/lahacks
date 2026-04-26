"""
Coordinator Agent — Chat Protocol entry point for ASI:One.

Full cascade:
  ASI:One → ChatMessage → Coordinator
  Coordinator → MarketIntelRequest  → Market Intelligence
  Market Intelligence → MarketIntelResponse → Coordinator
  Coordinator → ForecastRequest → Demand Planning
  Demand Planning → ForecastResponse → Coordinator
  Coordinator → InventoryAssessmentRequest → Inventory Manager
  Inventory Manager → InventoryAssessmentResponse → Coordinator
  Coordinator → FreightAnalysisRequest → Shipment Analyst
  Shipment Analyst → FreightAnalysisResponse → Coordinator
  Coordinator → ChatMessage (synthesis reply) → ASI:One
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

_PROMPT_CONFIG_PATH = Path(__file__).resolve().parent / "prompt_config.json"


def _load_prompt_config() -> dict:
    try:
        return json.loads(_PROMPT_CONFIG_PATH.read_text())
    except Exception:
        return {}


def _cfg(key: str, fallback: str = "") -> str:
    return _load_prompt_config().get(key, fallback)

import httpx
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

asyncio.set_event_loop(asyncio.new_event_loop())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agents.common.llm_client import generate_reasoning
from agents.demand_planning.logic import run_demand_planning
from agents.inventory_manager.logic import run_inventory_assessment
from agents.market_intelligence.logic import run_market_intelligence
from agents.shipment_analyst.logic import run_freight_analysis
from shared.contracts import AgentDecision

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Guard against mailbox re-delivery while a slow Ollama cascade is in-flight
_processing: set[str] = set()

coordinator = Agent(
    name="supplymind_coordinator",
    seed="coordinator_seed_supplymind_2024",
    port=8003,
    mailbox=True,
)

chat_proto = Protocol(spec=chat_protocol_spec)


async def _run_cascade(ctx: Context) -> str:
    """Run all 4 agent logics inline, post each decision, return the synthesis reply."""
    cfg = _load_prompt_config()

    async def _post(decision: AgentDecision) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"{BACKEND_URL}/api/decisions",
                    content=decision.model_dump_json(),
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                ctx.logger.error("Failed to post decision: %s", exc)

    # Stage 1 — Market Intelligence
    market_decision = run_market_intelligence()
    await _post(market_decision)
    ctx.logger.info("Market Intelligence complete")

    # Stage 2 — Demand Planning
    demand_decision = run_demand_planning()
    await _post(demand_decision)
    ctx.logger.info("Demand Planning complete")

    # Stage 3 — Inventory Assessment
    inventory_decision = run_inventory_assessment(demand_decision.model_dump())
    await _post(inventory_decision)
    ctx.logger.info("Inventory Assessment complete")

    # Stage 4 — Freight Analysis
    active_signals = market_decision.outputs.get("active_signals", [])
    flags = inventory_decision.outputs.get("flags", [])
    freight_decision = run_freight_analysis(flags, active_signals)
    await _post(freight_decision)
    ctx.logger.info("Freight Analysis complete")

    # Stage 5 — Synthesis reply
    at_risk = inventory_decision.outputs.get("at_risk_count", 0)
    savings = freight_decision.outputs.get("total_savings_usd", 0.0)
    rerouted = freight_decision.outputs.get("rerouted_count", 0)

    persona = cfg.get(
        "agent_persona",
        "You are SupplyMind, an AI supply chain orchestrator for Diamond Foods.",
    )
    instructions = cfg.get(
        "synthesis_instructions",
        "Write a concise 2-3 sentence reply. Lead with the most critical finding. "
        "Reply in first person. Do not use bullet points.",
    )
    context_template = cfg.get("synthesis_context", "")
    context_filled = (
        context_template.format(rerouted_count=rerouted, savings=savings)
        if context_template else ""
    )

    synthesis_prompt = (
        f"{persona}\n"
        f"{instructions}\n\n"
        f"Market: {market_decision.summary}\n"
        f"Demand: {demand_decision.summary}\n"
        f"Inventory: {inventory_decision.summary}\n"
        f"Freight: {freight_decision.summary}\n"
        + (f"\n{context_filled}" if context_filled else "")
    )
    reply_text = generate_reasoning(synthesis_prompt)

    synthesis_decision = AgentDecision(
        agent_name="coordinator",
        decision_type="synthesis",
        summary=(
            f"Full cascade complete: 340% demand spike on SKU-4471, "
            f"{at_risk} at-risk SKUs, ${savings:,.0f} freight savings."
        ),
        reasoning=reply_text,
        confidence=0.93,
        inputs_considered=[
            "market_intelligence decision",
            "demand_planning decision",
            "inventory_manager decision",
            "shipment_analyst decision",
        ],
        outputs={
            "cascade_complete": True,
            "at_risk_count": at_risk,
            "excess_count": inventory_decision.outputs.get("excess_count", 0),
            "total_savings_usd": savings,
            "rerouted_count": rerouted,
        },
        timestamp=datetime.now(timezone.utc),
        downstream_targets=[],
    )
    await _post(synthesis_decision)
    ctx.logger.info("Synthesis complete — reply ready")

    return reply_text


@coordinator.on_event("startup")
async def on_startup(ctx: Context) -> None:
    ctx.logger.info("Coordinator ready. Address: %s", ctx.agent.address)


# ---------------------------------------------------------------------------
# Chat Protocol — entry point from ASI:One
# ---------------------------------------------------------------------------

async def _cascade_and_reply(ctx: Context, sender: str, msg_key: str, user_text: str) -> None:
    try:
        reply_text = await _run_cascade(ctx)
    except Exception as exc:
        ctx.logger.error("Cascade failed: %s", exc)
        reply_text = _cfg(
            "no_results_reply",
            "I was unable to complete the supply chain analysis. Please try again.",
        )
    finally:
        _processing.discard(msg_key)

    await ctx.send(sender, ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=reply_text)],
    ))
    ctx.logger.info("Reply sent to %s", sender)


@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage) -> None:
    # Ack immediately — this marks the message as processed in the mailbox
    # so re-polls don't re-deliver it while the slow Ollama cascade runs.
    await ctx.send(sender, ChatAcknowledgement(
        timestamp=datetime.now(timezone.utc),
        acknowledged_msg_id=msg.msg_id,
    ))

    msg_key = str(msg.msg_id)
    if msg_key in _processing:
        ctx.logger.info("Duplicate delivery of %s — skipping", msg_key)
        return
    _processing.add(msg_key)

    text_parts = [c.text for c in msg.content if isinstance(c, TextContent)]
    user_text = " ".join(text_parts).strip() or "(no text)"
    ctx.logger.info("Chat from %s: %s", sender, user_text[:120])

    # Fire cascade in the background so this handler returns immediately.
    # uAgents will not re-deliver the message because the ack was already sent.
    asyncio.create_task(_cascade_and_reply(ctx, sender, msg_key, user_text))


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
    ctx.logger.debug("Ack from %s for msg %s", sender, msg.acknowledged_msg_id)


# ---------------------------------------------------------------------------
# Register chat protocol
# ---------------------------------------------------------------------------
coordinator.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    coordinator.run()
