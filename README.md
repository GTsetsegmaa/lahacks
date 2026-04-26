# SupplyMind

**SupplyMind** is a multi-agent AI system that automates push-based supply chain decisions for perishable goods companies. Five specialized agents — built on Fetch.ai uAgents and registered on Agentverse — continuously monitor demand signals, inventory positions, freight markets, and external events, then surface ranked action recommendations to buyers via ASI:One chat or a live Next.js dashboard. The entire stack, including local Gemma 3 inference, runs on a single ASUS Ascent GX10 with zero cloud egress during a demo.

> Built at **LaHacks 2026** by a 2-person team in 36 hours.

---

## Prize tracks

| # | Track | How SupplyMind qualifies |
|---|-------|--------------------------|
| 1 | **Fetch.ai — Best Use of Agentverse / ASI:One** | Coordinator agent registered on Agentverse via Chat Protocol. Any ASI:One user can message it in natural language and receive a fully synthesised supply chain brief. |
| 2 | **ASUS Ascent GX10 — Edge AI** | All five agents, the FastAPI backend, and the Next.js dashboard run containerised on a single GX10. Gemma 3 inference runs on the GX10 NPU via Ollama — no network calls leave the device during a demo. |
| 3 | **MLH — Best Use of Google Gemma** | Gemma 3 (via Ollama) powers all five agent reasoning tasks: market signal interpretation, demand spike classification, vendor risk narrative, freight consolidation justification, and synthesis. Deterministic math stays in Python. |
| 4 | **MLH — Best Use of MongoDB** | Agent decisions are persisted to MongoDB Atlas (with a local JSON fallback). The dashboard replays the full decision history on reconnect via `/api/decisions`. |
| 5 | **MLH — Best Use of ElevenLabs** | Dashboard Demo Mode auto-narrates each agent decision via ElevenLabs TTS (Web Speech API fallback) as the cascade streams in, giving live voice commentary during judging. |

---

## Architecture

```
                        ┌──────────────────────────────────────────────────────┐
                        │                  ASUS Ascent GX10                    │
                        │                                                      │
  ┌──────────┐          │  ┌────────────────────────────────────────────────┐  │
  │ ASI:One  │─────────▶│  │               Coordinator                     │  │
  │ (chat)   │◀─────────│  │       uAgent · Chat Protocol · mailbox=True    │  │
  └──────────┘          │  └──┬──────────┬──────────┬──────────┬───────────┘  │
   Agentverse           │     │(1)        │(2)        │(3)        │(4)         │
                        │     ▼           ▼           ▼           ▼           │
                        │  ┌──────┐  ┌────────┐  ┌─────────┐  ┌────────┐    │
                        │  │Market│  │ Demand │  │Inventory│  │Freight │    │
                        │  │Intel │  │Planning│  │ Manager │  │Analyst │    │
                        │  └──┬───┘  └───┬────┘  └────┬────┘  └───┬────┘    │
                        │     └──────────┴─────────────┴───────────┘         │
                        │                     │ POST /api/decisions            │
                        │              ┌──────▼──────┐      ┌──────────────┐  │
                        │              │  FastAPI    │◀────▶│  Ollama      │  │
                        │              │  Backend    │      │  (Gemma 3)   │  │
                        │              └──────┬──────┘      └──────────────┘  │
                        │                     │ SSE /api/stream                │
                        │              ┌──────▼──────┐                        │
                        │              │  Next.js    │                        │
                        │              │  Dashboard  │                        │
                        │              └─────────────┘                        │
                        └──────────────────────────────────────────────────────┘
```

### Agent responsibilities

| Agent | Domain | Never touches |
|---|---|---|
| **Coordinator** | Chat Protocol entry, cascade routing, synthesis reply | Business logic |
| **Market Intelligence** | External signals, fuel surcharges, weather | Inventory records |
| **Demand Planning** | 7-day SKU forecasts, spike detection, promo overlay | Carrier selection |
| **Inventory Manager** | Days-of-supply, FIFO, at-risk / excess flags | Demand signals |
| **Shipment Analyst** | Route optimization, mode switching, cost savings | Vendor relationships |

Full sequence diagram and technical writeup: [`docs/architecture.md`](docs/architecture.md)

---

## Tech stack

| Layer | Technology |
|---|---|
| Agent framework | Fetch.ai uAgents 0.24 + Agentverse Chat Protocol |
| LLM | Gemma 3 via Ollama (NPU on GX10) |
| Backend | FastAPI 0.111 + SSE (sse-starlette) |
| Frontend | Next.js 14 App Router · TypeScript · Tailwind CSS |
| Data contracts | Pydantic v2 (Python) + TypeScript mirror |
| Database | MongoDB Atlas / local JSON fallback |
| Voice | ElevenLabs TTS / Web Speech API fallback |
| Containers | Docker Compose |
| Hardware | ASUS Ascent GX10 (Ubuntu 24.04) |

---

## Repo structure

```
supplymind/
├── agents/
│   ├── coordinator/        ← Chat Protocol entry point, Agentverse-registered
│   ├── market_intelligence/
│   ├── demand_planning/
│   ├── inventory_manager/
│   ├── shipment_analyst/
│   ├── common/
│   │   ├── llm_client.py   ← Ollama/Gemma 3 wrapper with context-aware fallback
│   │   └── messages.py     ← uAgent message models
│   └── run.py              ← Supervisor: starts all 5 agents as subprocesses
├── backend/
│   └── main.py             ← FastAPI: decisions, SSE stream, cascade triggers
├── dashboard/
│   ├── app/
│   │   ├── page.tsx        ← Overview (KPIs, pipeline status, action items)
│   │   ├── activity/       ← Live decision feed
│   │   ├── plan/           ← Replenishment purchase order table
│   │   └── demo/script/    ← Presenter rehearsal tool
│   ├── components/
│   │   ├── DecisionCard.tsx
│   │   ├── SavingsCounter.tsx   ← Animated $0 → $3,421 counter
│   │   └── DemoToggle.tsx
│   └── contexts/
│       └── DemoContext.tsx      ← Demo mode: seeded text, 3 s pacing, TTS
├── shared/
│   ├── contracts.py        ← Pydantic models — single source of truth
│   ├── contracts.ts        ← TypeScript mirror
│   └── mock_data/          ← Synthetic JSON: SKUs, shipments, inventory, freight
├── docs/
│   └── architecture.md
├── docker-compose.yml
└── requirements.txt
```

---

## Setup — local development

**Prerequisites:** Python 3.12+, Node.js 20+, [Ollama](https://ollama.ai), Docker Desktop

```bash
# 1. Install dependencies
pip install -r requirements.txt
cd dashboard && npm install && cd ..

# 2. Environment
cp .env.example .env
# Minimum required: nothing — all defaults work out of the box.
# Add ELEVENLABS_API_KEY for voice narration in Demo Mode.

# 3. Generate mock data
python shared/generate_mock_data.py

# 4. Pull and start Ollama
ollama pull gemma3
ollama serve

# 5a. Run with Docker (recommended)
docker compose up --build

# 5b. Or run without Docker
uvicorn backend.main:app --reload --port 8000   # terminal 1
python -m agents.run                             # terminal 2
cd dashboard && npm run dev                      # terminal 3
```

| URL | What |
|-----|------|
| http://localhost:3000 | Dashboard |
| http://localhost:3000/demo/script | Presenter rehearsal tool |
| http://localhost:8000/docs | FastAPI interactive docs |

---

## Setup — ASUS Ascent GX10

```bash
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull gemma3

# 2. Install Docker
sudo apt install docker.io docker-compose-plugin -y
sudo usermod -aG docker $USER && newgrp docker

# 3. Clone, configure, start
git clone <repo-url> && cd supplymind
cp .env.example .env
docker compose up --build -d

# 4. Verify
curl http://localhost:8000/docs
```

`extra_hosts: host.docker.internal:host-gateway` in `docker-compose.yml` lets agent containers reach the Ollama process on the host without any `/etc/hosts` edits.

**Memory budget (all containers):** ~3 GB RAM, plus NPU VRAM for Gemma 3 weights.

---

## Demo scenario

The judging demo runs this exact flow (~3 minutes). Open `/demo/script` in a second window for speaker notes and a live countdown timer.

| Time | Event | Talking point |
|------|-------|---------------|
| 0:00 | Overview page — all KPIs at zero | "Clean state — no cascade has run yet" |
| 0:30 | Activity Log → click **Run Demo** | Demo Mode on: seeded text, 3 s pacing, voice narration |
| 1:00 | Market Intelligence fires | Fuel surcharge +18% on Gulf Coast-Midwest truck lane |
| 1:03 | Demand Planning fires | SKU-4471 at 340% of 90-day baseline (Thanksgiving + promo) |
| 1:06 | Inventory Manager fires | 3 SKUs at stockout risk; SKU-4471 depletes in 2.1 days |
| 1:09 | Shipment Analyst fires | 2 POs → intermodal — **$3,421 freight savings** |
| 1:12 | Coordinator synthesis | Full brief; this is what ASI:One returns to a buyer |
| 1:30 | Navigate to Overview | Savings counter animates $0 → $3,421 |
| 2:00 | Navigate to Plan | Purchase orders pre-staged, costs estimated |
| 3:00 | ASI:One live chat | Ask coordinator "What's my biggest risk this week?" |

**The money moment:** $3,421 in freight savings, identified automatically. Two Gulf Coast→Midwest shipments switched from truck ($3,540/shipment) to intermodal ($1,830/shipment) after the Market Intelligence agent detected the fuel surcharge spike. Computed locally. No API calls.

---

## API quick reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/decisions` | Agents post `AgentDecision` objects |
| `GET` | `/api/decisions` | Retrieve all stored decisions |
| `GET` | `/api/stream` | SSE — replays history then streams live |
| `POST` | `/api/trigger/cascade` | Full 5-agent cascade (live Ollama) |
| `POST` | `/api/trigger/demo` | Seeded cascade, 3 s pacing (no LLM call) |
| `GET` | `/api/replenishment-plan` | Purchase orders from current inventory state |

---

## Team & acknowledgments

Built at LaHacks 2026.

Thanks to [Fetch.ai](https://fetch.ai) for uAgents and Agentverse, [ASUS](https://www.asus.com) for the GX10 hardware, [Google](https://ai.google.dev/gemma) for Gemma 3, [Ollama](https://ollama.ai) for local inference, [ElevenLabs](https://elevenlabs.io) for voice synthesis, [MongoDB](https://mongodb.com) for Atlas, and [Vercel](https://vercel.com) for Next.js.
