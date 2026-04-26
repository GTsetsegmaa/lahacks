"""
Coordinator Agent — Chat Protocol entry point for ASI:One.

Flow (this vertical slice):
  ASI:One → ChatMessage → Coordinator
  Coordinator → ForecastRequest → Demand Planning Agent
  Demand Planning Agent → ForecastResponse → Coordinator
  Coordinator → ChatMessage (natural-language reply) → ASI:One
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

# Python 3.14: must set event loop before any uagents import creates an Agent
asyncio.set_event_loop(asyncio.new_event_loop())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agents.common.llm_client import generate_reasoning
from agents.common.messages import ForecastRequest, ForecastResponse

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Resolve demand planning agent address from its fixed seed (deterministic,
# no network call required — address derivation is purely local crypto)
# ---------------------------------------------------------------------------
_tmp = Agent(name="demand_planning", seed="demand_planning_seed_supplymind_2024")
DEMAND_PLANNING_ADDRESS = _tmp.address
del _tmp

coordinator = Agent(
    name="supplymind_coordinator",
    seed="coordinator_seed_supplymind_2024",
    port=8003,
    mailbox=True,   # mailbox=True without explicit endpoint — port is sufficient
)

chat_proto = Protocol(spec=chat_protocol_spec)


@coordinator.on_event("startup")
async def on_startup(ctx: Context) -> None:
    ctx.logger.info("Coordinator ready.  Address : %s", ctx.agent.address)
    ctx.logger.info("Demand Planning at: %s", DEMAND_PLANNING_ADDRESS)


# ---------------------------------------------------------------------------
# Chat Protocol handlers
# ---------------------------------------------------------------------------

@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage) -> None:
    # 1. Acknowledge immediately so ASI:One knows the message was received
    await ctx.send(sender, ChatAcknowledgement(
        timestamp=datetime.now(timezone.utc),
        acknowledged_msg_id=msg.msg_id,
    ))

    # 2. Extract text content (ignore non-text content types for now)
    text_parts = [c.text for c in msg.content if isinstance(c, TextContent)]
    user_text = " ".join(text_parts).strip() or "(no text content)"
    ctx.logger.info("Chat from %s: %s", sender, user_text[:120])

    # 3. Store chat sender so we can reply once the decision arrives
    ctx.storage.set("pending_chat_sender", sender)
    ctx.storage.set("pending_msg_id", str(msg.msg_id))

    # 4. Kick off the agent cascade — demand planning first
    await ctx.send(DEMAND_PLANNING_ADDRESS, ForecastRequest(requester="coordinator", week=47))


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
    ctx.logger.debug("Ack from %s for msg %s", sender, msg.acknowledged_msg_id)


# ---------------------------------------------------------------------------
# Specialist agent response handler
# ---------------------------------------------------------------------------

@coordinator.on_message(model=ForecastResponse)
async def handle_forecast_response(ctx: Context, sender: str, msg: ForecastResponse) -> None:
    ctx.logger.info("ForecastResponse received from %s", sender)

    chat_sender = ctx.storage.get("pending_chat_sender")
    if not chat_sender:
        ctx.logger.warning("ForecastResponse arrived but no pending chat sender in storage.")
        return

    # Synthesise natural-language reply via LLM (falls back to stub if Ollama unavailable)
    prompt = (
        "You are SupplyMind, an AI supply chain orchestrator for Diamond Foods. "
        "Write a concise 2-3 sentence reply to a supply chain manager who asked for "
        "this week's replenishment plan. Focus on the most critical finding and "
        "recommend the immediate action.\n\n"
        f"Forecast summary: {msg.summary}\n"
        f"Key finding: {msg.key_finding}\n\n"
        "Reply in first person. Do not use bullet points."
    )
    reply_text = generate_reasoning(prompt)

    await ctx.send(chat_sender, ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=reply_text)],
    ))
    ctx.logger.info("Reply sent to %s", chat_sender)

    # Clear pending state
    ctx.storage.set("pending_chat_sender", None)
    ctx.storage.set("pending_msg_id", None)


# ---------------------------------------------------------------------------
# Register chat protocol with the agent
# ---------------------------------------------------------------------------
coordinator.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    coordinator.run()
