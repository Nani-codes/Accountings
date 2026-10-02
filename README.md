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

## Local setup

```bash
cp .env.example .env
docker compose up -d
cd apps/api && uv sync
uv run uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd apps/web && npm install && npm run dev
```

- API health: http://localhost:8000/health
- Web: http://localhost:3000
- MinIO console: http://localhost:9001 (minio / minio12345)

## Design system

UI tokens follow Trilolabs Tripundra Clarity (void / ash / Shiva blue, Manrope). See product `DESIGN.md` at repo root when present.
