#!/usr/bin/env python3
"""
Register the Coordinator on Agentverse so ASI:One can find and chat with it.

Requirements:
  - Coordinator agent must be RUNNING before you call this script.
  - AGENTVERSE_KEY must be set in your .env (get it from agentverse.ai → API Keys).

Usage:
  python agents/coordinator/register.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from uagents_core.utils.registration import (
    RegistrationRequestCredentials,
    register_chat_agent,
)

AGENTVERSE_KEY = os.environ.get("AGENTVERSE_KEY", "")
AGENT_SEED = "coordinator_seed_supplymind_2024"
AGENT_NAME = "SupplyMind Coordinator"
AGENT_ENDPOINT = "http://localhost:8003/submit"

if not AGENTVERSE_KEY:
    print("ERROR: AGENTVERSE_KEY is not set. Add it to your .env file.")
    print("Get your key at: https://agentverse.ai → Settings → API Keys")
    sys.exit(1)

print(f"Registering '{AGENT_NAME}' at {AGENT_ENDPOINT} …")

register_chat_agent(
    AGENT_NAME,
    AGENT_ENDPOINT,
    active=True,
    credentials=RegistrationRequestCredentials(
        agentverse_api_key=AGENTVERSE_KEY,
        agent_seed_phrase=AGENT_SEED,
    ),
)

print("Registration complete. Your agent should now appear in the Agentverse marketplace.")
print("Search for 'SupplyMind Coordinator' in ASI:One to start a chat.")
