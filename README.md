# Accountings

Monorepo for **Accountings** ([accountings.in](https://accountings.in)) — a [Trilolabs](https://www.trilolabs.com) product: deterministic Purchase ↔ GSTR-2B reconciliation, Agno explanations on AgentOS, and a thin Next.js UI.

## Structure

- `apps/api` — FastAPI product API (AgentOS mounted in a later task)
- `apps/web` — Next.js App Router UI (Tripundra Operate density)
- `docs/superpowers` — design spec and implementation plan

## Prerequisites

- Docker / Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python 3.12+)
- Node.js 20+
- Google Cloud project with Vertex AI API enabled + service account JSON

## Local setup

```bash
cp .env.example .env
# Set GOOGLE_APPLICATION_CREDENTIALS to your Vertex service-account JSON path
# (never commit the key file)
docker compose up -d
cd apps/api && uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd apps/web && cp .env.local.example .env.local && npm install && npm run dev
```

Agent UI (optional Agno control-plane chat on `:3001`; workbench **Advisor** is first-party):

```bash
cd apps/agent-ui && cp .env.local.example .env.local && pnpm install && pnpm dev
```

- API health: http://localhost:8000/health
- AgentOS config: http://localhost:8000/config
- Web: http://localhost:3000 (Accountings UI)
- Agent UI (optional): http://localhost:3001
- Postgres host port: **5433** (avoids clashes with other local Postgres)
- MinIO: host **9010** / console **9011** (optional for local S3). For **real AWS S3**, set `STORAGE_BACKEND=s3`, leave `S3_ENDPOINT` empty, and set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (or `AWS_ACCESS_SECRET`) / `AWS_BUCKET_NAME` / `AWS_REGION`. Client GST uploads and run exports read/write via this storage layer; `/health` reports the active backend (no secrets).
- LLM: **Vertex AI Gemini** (`VERTEX_MODEL_ID`, default `gemini-2.5-flash`) via Agno
- CORS: include both `:3000` (workbench) and `:3001` (optional Agent UI) in `API_CORS_ORIGINS`
- **TallyPrime hosted connector:** The Accountings Connector runs on the firm PC and dials out to this API via WebSocket. Advisor can call `tally_*` tools to query live ledgers, day book, trial balance. Set `TALLY_TOKEN_PEPPER` for pairing security. `/health` reports `tally_connector: enabled`.

## Settings → Tally connector

1. **Pairing:** In the web UI, go to **Settings → Connect** and copy the pairing code.
2. **Download connector:** Use `TALLY_CONNECTOR_DOWNLOAD_URL` to get the Windows connector executable.
3. **Run connector:** On the firm PC, run the connector with the pairing code. It will dial out to this API via WebSocket.
4. **Status:** Once connected, Advisor can query live Tally data (ledgers, day book, trial balance). Status shows as **Online** in Settings.
5. **Disconnect:** Revokes the pairing code and closes the WebSocket session.

## Demo path

1. Sign up at `/login`
2. Create a client
3. Upload Purchase + GSTR-2B (CSV from `fixtures/recon/tiny_pair`)
4. Review findings → accept → generate client request → export Excel/PDF
5. Open **Advisor** (`/assistant`) — uses AgentOS `/agents/ca-advisor/runs` + `/sessions` for history
6. (Optional) With Accountings Connector running on the firm PC, ask Advisor for ledger / day-book lookups from the connected company

## What we measure in pilot

- Finding accept+edit rate (trust)
- Runs / firm / month
- Time-to-reviewed (qualitative in week 4)

## Non-goals (v1)

No billing, WhatsApp, multi-user roles, or autonomous matching agents. Live Tally is **optional** via MCP (not required for recon); recon still runs on uploaded registers.
