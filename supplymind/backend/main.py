"""SupplyMind FastAPI backend — receives AgentDecisions, broadcasts via SSE."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared.contracts import AgentDecision

app = FastAPI(title="SupplyMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store (replaced by MongoDB when MONGODB_URI is set — future task)
_decisions: list[AgentDecision] = []
_subscribers: list[asyncio.Queue] = []


async def _broadcast(payload: str) -> None:
    for q in _subscribers:
        await q.put(payload)


@app.post("/api/decisions", status_code=201)
async def post_decision(decision: AgentDecision) -> dict:
    _decisions.append(decision)
    await _broadcast(decision.model_dump_json())
    return {"status": "accepted", "total": len(_decisions)}


@app.get("/api/decisions")
async def get_decisions() -> list[AgentDecision]:
    return _decisions


@app.get("/api/stream")
async def stream_decisions(request: Request) -> EventSourceResponse:
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.append(queue)

    async def generator() -> AsyncGenerator[dict, None]:
        try:
            # Replay all stored decisions to new subscriber
            for d in _decisions:
                yield {"data": d.model_dump_json()}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {"data": payload}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}  # keep-alive
        finally:
            _subscribers.remove(queue)

    return EventSourceResponse(generator())


# ---------------------------------------------------------------------------
# HTTP fallback trigger — "Run Demo" path (PROJECT.md hard rule 7)
# Also used by agents/trigger_demand.py when uAgent discovery is unavailable
# ---------------------------------------------------------------------------
@app.post("/api/trigger/demand", status_code=202)
async def trigger_demand() -> dict:
    """Invoke demand planning logic directly and post the decision."""
    from agents.demand_planning.logic import run_demand_planning  # lazy import

    decision = run_demand_planning()
    _decisions.append(decision)
    await _broadcast(decision.model_dump_json())
    return {"status": "triggered", "summary": decision.summary}
