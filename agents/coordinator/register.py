#!/usr/bin/env python3
"""
Register the SupplyMind Coordinator on Agentverse.

Requirements:
  - Coordinator must be RUNNING (python agents/run.py) before calling this.
  - AGENTVERSE_KEY in .env (agentverse.ai → Settings → API Keys)
  - AGENT_SEED_PHRASE in .env (the coordinator's seed phrase)

Usage:
  python agents/coordinator/register.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from uagents_core.utils.registration import (
    RegistrationRequestCredentials,
    register_chat_agent,
)

AGENTVERSE_KEY = os.environ.get("AGENTVERSE_KEY") or os.environ.get("ASI_ONE_API_KEY", "")
AGENT_SEED_PHRASE = os.environ.get("AGENT_SEED_PHRASE", "coordinator_seed_supplymind_2024")

COORDINATOR_ADDRESS = "agent1qd3h050w5h39ynpfe5feyq6nt47v7xvtszt2j8yjkmvme6kfxm5d7ckaddr"
INSPECTOR_URL = (
    f"https://agentverse.ai/inspect/"
    f"?uri=http%3A//127.0.0.1%3A8003"
    f"&address={COORDINATOR_ADDRESS}"
)

if not AGENTVERSE_KEY:
    print("ERROR: AGENTVERSE_KEY is not set. Add it to your .env file.")
    print("Get your key at: https://agentverse.ai → Settings → API Keys")
    sys.exit(1)

print("Registering SupplyMind Coordinator on Agentverse …")

register_chat_agent(
    "SupplyMind Coordinator",
    INSPECTOR_URL,
    active=True,
    credentials=RegistrationRequestCredentials(
        agentverse_api_key=AGENTVERSE_KEY,
        agent_seed_phrase=AGENT_SEED_PHRASE,
    ),
)

print(f"Done. Address: {COORDINATOR_ADDRESS}")
print("The coordinator is now discoverable on Agentverse and via ASI:One.")
