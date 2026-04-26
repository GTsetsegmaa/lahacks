"""LLM client — two paths:

  1. async query_asi1(ctx, prompt)  — uAgents Chat Protocol, used by the coordinator
     which is already a registered mailbox agent. ASI-1 address is the model.

  2. generate_reasoning(prompt)     — REST API, used by the FastAPI backend
     which has no uAgent context.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

import requests

logger = logging.getLogger(__name__)

# Matches the env var name used in the ASI-1 docs
ASI1_API_KEY = (
    os.getenv("ASI_ONE_API_KEY") or
    os.getenv("ASI1_API_KEY") or
    ""
)
ASI1_API_URL = "https://api.asi1.ai/v1/chat/completions"
ASI1_MODEL   = os.getenv("ASI1_MODEL", "asi1")

# uAgents Chat Protocol destination — ASI-1 agent address on Agentverse
ASI1_ADDRESS = os.getenv(
    "ASI1_AGENT_ADDRESS",
    "agent1qd3h050w5h39ynpfe5feyq6nt47v7xvtszt2j8yjkmvme6kfxm5d7ckaddr",
)

OLLAMA_URL   = os.getenv("LLM_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("LLM_MODEL", "gemma3")

# Single pending slot — cascade is sequential so only one LLM call is in-flight.
_pending: asyncio.Future[str] | None = None


async def query_asi1(ctx, prompt: str) -> str:  # ctx: uagents.Context
    """Send prompt to ASI-1 via Fetch.ai Chat Protocol; await the response."""
    from uagents_core.contrib.protocols.chat import ChatMessage, TextContent

    global _pending
    loop = asyncio.get_event_loop()
    _pending = loop.create_future()

    await ctx.send(
        ASI1_ADDRESS,
        ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=prompt)],
        ),
    )

    try:
        return await asyncio.wait_for(asyncio.shield(_pending), timeout=60.0)
    finally:
        _pending = None


def resolve_response(text: str) -> None:
    """Called by coordinator's message handler when ASI-1 replies."""
    global _pending
    if _pending is not None and not _pending.done():
        _pending.set_result(text)


def generate_reasoning(prompt: str) -> str:
    """REST call to ASI-1; falls back to Ollama if no API key is set."""
    if ASI1_API_KEY:
        resp = requests.post(
            ASI1_API_URL,
            headers={
                "Authorization": f"Bearer {ASI1_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": ASI1_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    import httpx
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 512},
            },
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
