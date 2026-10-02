# GST Workbench (AI GST Reconciliation MVP)

Monorepo for the CA firm workbench: deterministic Purchase ↔ GSTR-2B reconciliation, Agno explanations on AgentOS, and a thin Next.js UI.

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

- API health: http://localhost:8000/health
- Web: http://localhost:3000
- Postgres host port: **5433** (avoids clashes with other local Postgres)
- MinIO: host **9010** / console **9011** (`quay.io/minio/minio`)
- LLM: **Vertex AI Gemini** (`VERTEX_MODEL_ID`, default `gemini-2.5-flash`) via Agno

## Demo path

1. Sign up at `/login`
2. Create a client
3. Upload Purchase + GSTR-2B (CSV from `fixtures/recon/tiny_pair`)
4. Review findings → accept → generate client request → export Excel/PDF

## What we measure in pilot

- Finding accept+edit rate (trust)
- Runs / firm / month
- Time-to-reviewed (qualitative in week 4)

## Non-goals (v1)

No billing, WhatsApp, Tally, multi-user roles, or autonomous matching agents.
