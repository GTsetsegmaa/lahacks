# SupplyMind

Multi-agent push-based supply chain orchestrator for perishable goods companies.
Built on Fetch.ai uAgents for LaHacks 2026.

## Setup

### 1. Copy environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the following keys:

| Variable | Where to get it |
|---|---|
| `ELEVENLABS_API_KEY` | [elevenlabs.io](https://elevenlabs.io) → Profile → API Keys |
| `MONGODB_URI` | MongoDB Atlas cluster connection string (optional — falls back to local JSON) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) (hosted LLM fallback) |
| `ASI_ONE_API_KEY` | Fetch.ai Agentverse dashboard |
| `LLM_BASE_URL` | Leave as `http://localhost:11434` when running Ollama locally on the GX10 |

### 2. Generate mock data

```bash
pip install faker
python shared/generate_mock_data.py
```

### 3. Run with Docker

```bash
docker compose up --build
```

- Dashboard: http://localhost:3000
- Backend API: http://localhost:8000

### 4. Run without Docker (development)

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Dashboard (separate terminal)
cd dashboard
npm install
npm run dev
```
