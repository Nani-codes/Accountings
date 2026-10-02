# AI GST Reconciliation MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a CA workbench where a firm uploads Purchase + GSTR-2B (plus other slots), gets deterministic reconciliation, Agno-explained findings, client follow-ups, and a working-paper export.

**Architecture:** Monolith FastAPI product API mounted with own AgentOS (`base_app`); in-process Python recon engine (no LLM matching); thin Next.js UI (six screens) on Tripundra Operate density. Postgres + S3-compatible storage.

**Tech Stack:** Next.js, Tailwind, shadcn/ui, TanStack Query · FastAPI, SQLAlchemy/Alembic, pandas, openpyxl · PostgreSQL · S3-compatible storage · Agno Agents/Workflows + AgentOS · one OpenAI cloud model · pytest

**Spec:** `docs/superpowers/specs/2026-10-02-ai-gst-reconciliation-mvp-design.md`

## Global Constraints

- Matching is **Purchase Register ↔ GSTR-2B only**; LLM never does arithmetic/matching.
- Single user per organization; no billing, WhatsApp, Tally, or filing in v1.
- Auth: email/password **and** Google OAuth.
- Column mapping: hybrid templates + manual mapper; **no** AI column guessing.
- Finding gate: only `accepted` / `edited` findings enter client requests and working papers.
- Client responses pending = `client_requests.status == sent`.
- UI follows Tripundra Clarity in root `DESIGN.md` (void/ash/Shiva blue, Manrope).
- AgentOS mounted via `AgentOS(..., base_app=fastapi_app)` per [Bring Your Own FastAPI App](https://docs.agno.com/agent-os/custom-fastapi/overview).

---

## File structure (create)

```text
apps/api/
  pyproject.toml
  alembic.ini
  alembic/
  app/
    main.py                 # FastAPI + AgentOS get_app()
    config.py
    db.py
    models/                 # SQLAlchemy models
    schemas/                # Pydantic API schemas
    api/                    # routers: auth, clients, runs, findings, requests, dashboard
    services/               # storage, auth, mapping, exports, metrics
    recon/                  # pure engine: parse, normalize, match, group
    ai/                     # Agno agents, workflow, explain/client/working-paper
    tests/
apps/web/
  package.json
  src/app/                  # App Router pages for 6 screens
  src/components/
  src/lib/api.ts
  src/styles/globals.css    # Tripundra tokens
fixtures/recon/             # golden Purchase + 2B pairs + expected.json
docker-compose.yml          # postgres + minio for local
.env.example
```

---

### Task 1: Monorepo scaffold + local infra

**Files:**
- Create: `docker-compose.yml`, `.env.example`, `apps/api/pyproject.toml`, `apps/api/app/config.py`, `apps/api/app/main.py`, `apps/web/package.json`, `apps/web/src/app/layout.tsx`, `apps/web/src/styles/globals.css`, `README.md`

**Interfaces:**
- Produces: `Settings` from env; `app` FastAPI instance; `docker compose up` Postgres `5432` + MinIO `9000`

- [ ] **Step 1: Add docker-compose and env example**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: workbench
      POSTGRES_PASSWORD: workbench
      POSTGRES_DB: workbench
    ports: ["5432:5432"]
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: minio12345
    ports: ["9000:9000", "9001:9001"]
```

```bash
# .env.example
DATABASE_URL=postgresql+psycopg://workbench:workbench@localhost:5432/workbench
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio12345
S3_BUCKET=workbench
OPENAI_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
JWT_SECRET=dev-change-me
API_CORS_ORIGINS=http://localhost:3000
```

- [ ] **Step 2: Scaffold FastAPI app skeleton**

```python
# apps/api/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    openai_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    jwt_secret: str
    api_cors_origins: str = "http://localhost:3000"
    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
```

```python
# apps/api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

def create_base_app() -> FastAPI:
    app = FastAPI(title="GST Workbench API")
    origins = [o.strip() for o in settings.api_cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app

base_app = create_base_app()
app = base_app  # AgentOS wraps this in Task 10
```

`pyproject.toml` deps: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `pydantic-settings`, `python-jose`, `passlib[bcrypt]`, `httpx`, `boto3`, `pandas`, `openpyxl`, `agno[os,openai]`, `reportlab`, `pytest`, `pytest-asyncio`.

- [ ] **Step 3: Scaffold Next.js app with Tripundra tokens**

Create `apps/web` with Next.js App Router, Tailwind, Manrope. In `globals.css` define CSS variables from `DESIGN.md`: `--void #060606`, `--ash-bright #f2f0e8`, `--shiva-blue #0047ab`, etc. Root layout void background + Manrope.

- [ ] **Step 4: Verify health**

Run: `docker compose up -d && cd apps/api && uv sync && uv run uvicorn app.main:app --reload --port 8000`  
Then: `curl -s http://localhost:8000/health`  
Expected: `{"status":"ok"}`

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example apps/api apps/web README.md
git commit -m "chore: scaffold API, web app, and local infra"
```

---

### Task 2: Database models + Alembic migration

**Files:**
- Create: `apps/api/app/db.py`, `apps/api/app/models/*.py`, `apps/api/alembic/*`, `apps/api/tests/test_models_smoke.py`

**Interfaces:**
- Produces: SQLAlchemy models for all tables in the spec; `get_db()` dependency

- [ ] **Step 1: Write failing smoke test (tables importable)**

```python
# apps/api/tests/test_models_smoke.py
from app.models import Organization, User, Client, ReconciliationRun

def test_model_tablename():
    assert Organization.__tablename__ == "organizations"
    assert User.__tablename__ == "users"
    assert Client.__tablename__ == "clients"
    assert ReconciliationRun.__tablename__ == "reconciliation_runs"
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd apps/api && uv run pytest tests/test_models_smoke.py -v`  
Expected: FAIL (module not found)

- [ ] **Step 3: Implement models**

Enums (string): run status, finding status, client_request status, document type, match status / difference type.

Required columns (minimum):

```python
# apps/api/app/models/organization.py — id UUID PK, name, created_at
# user.py — id, organization_id FK, email unique, password_hash nullable, google_sub nullable, name
# client.py — id, organization_id, name, gstin nullable, services JSON (default ["GST"])
# client_document.py — id, client_id, run_id nullable, doc_type, storage_key, filename, parsed_stats JSON nullable
# column_mapping_profile.py — id, client_id, doc_type, mapping JSON, template_id nullable
# reconciliation_run.py — id, client_id, organization_id, period (YYYY-MM), status, summary JSON, error_message, started_at, completed_at
# invoice.py — id, run_id, source (purchase|gstr2b|sales), invoice_number, invoice_date, supplier_gstin, recipient_gstin, taxable_value, igst, cgst, sgst, cess, total, raw JSON
# reconciliation_result.py — id, run_id, purchase_invoice_id, gstr_invoice_id nullable, match_status, match_score, difference_amount, difference_type
# ai_finding.py — id, client_id, run_id, category, severity, title, description, evidence JSON, recommended_action, status
# client_request.py — id, client_id, run_id, finding_ids UUID[], body, status, response_note nullable
# audit_log.py — id, organization_id, actor_user_id, action, entity_type, entity_id, payload JSON, created_at
```

- [ ] **Step 4: Alembic initial migration + upgrade**

Run: `uv run alembic revision --autogenerate -m "initial"` then `uv run alembic upgrade head`  
Expected: all tables created

- [ ] **Step 5: Re-run smoke test + commit**

```bash
uv run pytest tests/test_models_smoke.py -v
git add apps/api && git commit -m "feat: add domain models and initial migration"
```

---

### Task 3: Auth (email/password + Google) + single-user org

**Files:**
- Create: `apps/api/app/services/auth.py`, `apps/api/app/api/auth.py`, `apps/api/app/schemas/auth.py`, `apps/api/tests/test_auth.py`
- Modify: `apps/api/app/main.py` (include router)

**Interfaces:**
- Produces: `POST /auth/signup`, `POST /auth/login`, `POST /auth/google`, `GET /auth/me`; `CurrentUser` dependency returning `User` with `organization_id`

- [ ] **Step 1: Write failing auth tests**

```python
def test_signup_creates_org_and_user(client):
    r = client.post("/auth/signup", json={
        "email": "ca@firm.test", "password": "secret123", "name": "Nani", "firm_name": "Nani & Co"
    })
    assert r.status_code == 201
    body = r.json()
    assert "access_token" in body
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "ca@firm.test"
    assert me.json()["organization"]["name"] == "Nani & Co"

def test_login_rejects_bad_password(client):
    client.post("/auth/signup", json={
        "email": "ca2@firm.test", "password": "secret123", "name": "A", "firm_name": "F"
    })
    r = client.post("/auth/login", json={"email": "ca2@firm.test", "password": "wrong"})
    assert r.status_code == 401
```

- [ ] **Step 2: Run tests — expect fail**

Run: `uv run pytest tests/test_auth.py -v`  
Expected: FAIL (404 or import)

- [ ] **Step 3: Implement auth service + routes**

- Hash passwords with bcrypt; JWT access tokens (`sub=user_id`, 7d).
- Signup: create `Organization` + `User` in one transaction.
- Google: verify ID token with `google_client_id`; find-or-create user by `google_sub` / email; create org on first login (`firm_name` from Google name + " Firm" if needed).
- `get_current_user` dependency; 401 if missing/invalid.

- [ ] **Step 4: Pass tests + commit**

```bash
uv run pytest tests/test_auth.py -v
git add apps/api && git commit -m "feat: add email/password and Google auth with single-user orgs"
```

---

### Task 4: Clients API + dashboard aggregates (backend)

**Files:**
- Create: `apps/api/app/api/clients.py`, `apps/api/app/api/dashboard.py`, `apps/api/app/schemas/clients.py`, `apps/api/tests/test_clients_dashboard.py`

**Interfaces:**
- Produces: `GET/POST /clients`, `GET /clients/{id}`; `GET /dashboard` → `{ clients, active_gst_reviews, exceptions, client_responses_pending, recent_activity[] }`

- [ ] **Step 1: Failing tests**

```python
def test_create_and_list_clients(auth_client):
    r = auth_client.post("/clients", json={"name": "ABC Pvt Ltd", "gstin": "29ABCDE1234F1Z5"})
    assert r.status_code == 201
    listed = auth_client.get("/clients")
    assert len(listed.json()) == 1

def test_dashboard_counts_sent_requests(auth_client, seed_sent_client_request):
    d = auth_client.get("/dashboard").json()
    assert d["client_responses_pending"] == 1
```

- [ ] **Step 2: Implement CRUD + dashboard queries**

Counts:
- `clients` = count clients for org
- `active_gst_reviews` = runs in `needs_review` or `ai_enriching` / `reconciling` / `parsing`
- `exceptions` = count `ai_findings` with status `pending` for org
- `client_responses_pending` = count `client_requests` with status `sent`
- `recent_activity` = last 10 runs/clients with short labels

- [ ] **Step 3: Pass tests + commit**

```bash
uv run pytest tests/test_clients_dashboard.py -v
git commit -am "feat: add clients API and dashboard aggregates"
```

---

### Task 5: Object storage + document upload + hybrid column mapping

**Files:**
- Create: `apps/api/app/services/storage.py`, `apps/api/app/recon/templates.py`, `apps/api/app/recon/mapper.py`, `apps/api/app/api/uploads.py`, `apps/api/tests/test_mapper.py`, `apps/api/tests/test_uploads.py`

**Interfaces:**
- Produces: `put_object(key, bytes) -> str`; `apply_mapping(df, mapping) -> list[dict]`; `POST /clients/{id}/runs` (create draft run); `POST /runs/{id}/documents` (multipart); `GET /mapping/templates`; `PUT /clients/{id}/mapping-profiles/{doc_type}`

- [ ] **Step 1: Failing mapper unit tests**

```python
import pandas as pd
from app.recon.mapper import apply_mapping, REQUIRED_FIELDS

def test_apply_mapping_renames_columns():
    df = pd.DataFrame({"Inv No": ["A-1"], "GSTIN": ["29ABCDE1234F1Z5"], "Taxable": [1000], "Date": ["2026-03-01"]})
    mapping = {"invoice_number": "Inv No", "supplier_gstin": "GSTIN", "taxable_value": "Taxable", "invoice_date": "Date"}
    rows = apply_mapping(df, mapping)
    assert rows[0]["invoice_number"] == "A-1"
    assert rows[0]["supplier_gstin"] == "29ABCDE1234F1Z5"

def test_apply_mapping_rejects_missing_required():
    df = pd.DataFrame({"Inv No": ["A-1"]})
    try:
        apply_mapping(df, {"invoice_number": "Inv No"})
        assert False, "expected ValueError"
    except ValueError as e:
        assert "supplier_gstin" in str(e)
```

- [ ] **Step 2: Implement templates + mapper**

Built-in templates (ids): `generic_purchase`, `generic_gstr2b`, `tally_purchase` — each a dict of required field → column name.  
`REQUIRED_FIELDS = ["invoice_number", "invoice_date", "supplier_gstin", "taxable_value", "cgst", "sgst", "igst", "total"]` (cgst/sgst/igst may default 0 if column absent only when template marks optional — for v1 require taxable + total; tax columns default 0).

Bank uploads: store only (`doc_type=bank_statement`), no mapping.  
Sales: same mapper as purchase.  
Previous recon: if columns match export schema (`match_status`, etc.) parse stats; else store-only flag in `parsed_stats={"stored_only": true}`.

- [ ] **Step 3: Upload API**

Multipart file → MinIO key `org/{org_id}/client/{client_id}/run/{run_id}/{doc_type}/{filename}` → `client_documents` row. Require purchase + gstr2b before `POST /runs/{id}/start`.

- [ ] **Step 4: Pass tests + commit**

```bash
uv run pytest tests/test_mapper.py tests/test_uploads.py -v
git commit -am "feat: add uploads, storage, and hybrid column mapping"
```

---

### Task 6: Invoice normalization + matching engine (TDD core)

**Files:**
- Create: `apps/api/app/recon/normalize.py`, `apps/api/app/recon/match.py`, `apps/api/app/recon/types.py`, `apps/api/tests/test_normalize.py`, `apps/api/tests/test_match.py`, `fixtures/recon/tiny_pair/`

**Interfaces:**
- Produces:
  - `normalize_invoice_number(s: str) -> str`
  - `to_invoice(row: dict) -> Invoice`
  - `reconcile(purchase: list[Invoice], gstr2b: list[Invoice], *, date_tolerance_days: int = 3, amount_tolerance: Decimal = Decimal("1.00")) -> ReconcileOutput`  
    where `ReconcileOutput` has `results: list[MatchResult]`, `summary: dict`

- [ ] **Step 1: Failing normalize tests**

```python
from app.recon.normalize import normalize_invoice_number

def test_normalize_strips_separators_and_case():
    assert normalize_invoice_number(" INV/001-A ") == "INV001A"
    assert normalize_invoice_number("inv001a") == "INV001A"
```

- [ ] **Step 2: Implement normalize + Invoice dataclass**

```python
@dataclass(frozen=True)
class Invoice:
    invoice_number: str
    invoice_date: date
    supplier_gstin: str
    recipient_gstin: str | None
    taxable_value: Decimal
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    cess: Decimal
    total: Decimal
    source_id: str | None = None
```

- [ ] **Step 3: Failing match tests (cover hierarchy + categories)**

```python
def test_exact_match_gstin_and_number():
    p = [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, cgst=90, sgst=90, total=1180)]
    b = [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, cgst=90, sgst=90, total=1180)]
    out = reconcile(p, b)
    assert out.summary["matched"] == 1
    assert out.results[0].match_status == "exact_match"

def test_missing_in_2b():
    out = reconcile([inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, total=1180)], [])
    assert out.results[0].match_status == "missing_in_2b"

def test_gstin_mismatch_same_normalized_number():
    # same normalized number, different GSTIN → gstin_mismatch (not missing)
    ...

def test_amount_mismatch():
    ...

def test_tax_mismatch():
    ...

def test_duplicate_purchase_rows():
    ...

def test_date_mismatch_beyond_tolerance():
    ...

def test_fuzzy_number_match_after_normalization_tier():
    # "INV-1" vs "INV1" same GSTIN → matched via tier 2
    ...
```

Implement matching tiers in order; each purchase invoice gets one best result. Difference types: `none|gstin|amount|tax|date|duplicate|credit_note|missing`.

- [ ] **Step 4: Golden tiny fixture**

Add `fixtures/recon/tiny_pair/purchase.csv`, `gstr2b.csv`, `expected.json` with counts. Test loads and asserts summary.

- [ ] **Step 5: Pass all recon tests + commit**

```bash
uv run pytest tests/test_normalize.py tests/test_match.py -v
git commit -am "feat: add deterministic invoice normalize and match engine"
```

---

### Task 7: Exception grouping (Python) + run orchestration service

**Files:**
- Create: `apps/api/app/recon/group.py`, `apps/api/app/services/run_pipeline.py`, `apps/api/app/api/runs.py`, `apps/api/tests/test_group.py`, `apps/api/tests/test_run_pipeline.py`

**Interfaces:**
- Produces: `group_exceptions(results, invoices) -> list[ExceptionGroup]`; `start_run(run_id)` advances `parsing → reconciling → ai_enriching → needs_review|failed`; persists invoices + results; calls AI enrich (stub ok until Task 10)

```python
@dataclass
class ExceptionGroup:
    category: str
    supplier_gstin: str | None
    supplier_key: str
    invoice_count: int
    potential_itc: Decimal
    evidence: dict  # invoice ids, sample diffs
```

- [ ] **Step 1: Failing group test**

```python
def test_groups_gstin_mismatches_by_supplier():
    # three gstin_mismatch results same purchase supplier → one group invoice_count=3
    ...
```

- [ ] **Step 2: Implement grouping**

Group keys: `(category, supplier_gstin or "unknown")` for actionable statuses only (exclude `exact_match`).

- [ ] **Step 3: Pipeline service**

On `POST /runs/{id}/start`:
1. status `parsing` — load docs, map, write invoices (purchase/2b/sales); bank skip parse; previous optional
2. status `reconciling` — `reconcile(...)`; write `reconciliation_results` + summary JSON
3. status `ai_enriching` — call `enrich_findings(run_id)` (Task 10); on AI failure keep results, set `summary["ai_incomplete"]=true`, still `needs_review`
4. status `needs_review`

Parse errors → do not leave `uploading`; return 400 with field errors; run `failed` only for unexpected recon errors.

- [ ] **Step 4: Pass tests + commit**

```bash
uv run pytest tests/test_group.py tests/test_run_pipeline.py -v
git commit -am "feat: add exception grouping and run pipeline"
```

---

### Task 8: Findings review API + client request state machine

**Files:**
- Create: `apps/api/app/api/findings.py`, `apps/api/app/api/client_requests.py`, `apps/api/app/services/findings.py`, `apps/api/tests/test_findings_requests.py`

**Interfaces:**
- Produces:
  - `GET /runs/{id}/findings`
  - `PATCH /findings/{id}` body `{status, title?, description?, recommended_action?}` — `edited` if text changed while accepting
  - `POST /runs/{id}/client-requests` — **only** findings in `accepted|edited`; else 400
  - `PATCH /client-requests/{id}` status transitions: `draft→approved→sent→response_received|resolved` (allow `approved→sent`, `sent→response_received`, `response_received→resolved`; optional `response_note`)
  - When all findings dispositioned, set run `reviewed`

- [ ] **Step 1: Failing tests**

```python
def test_client_request_rejects_pending_only(auth_client, run_with_pending_finding):
    r = auth_client.post(f"/runs/{run_id}/client-requests", json={})
    assert r.status_code == 400

def test_accept_all_marks_run_reviewed(auth_client, run_with_two_findings):
    for fid in finding_ids:
        auth_client.patch(f"/findings/{fid}", json={"status": "accepted"})
    assert auth_client.get(f"/runs/{run_id}").json()["status"] == "reviewed"

def test_sent_request_counts_on_dashboard(auth_client, ...):
    ...
```

- [ ] **Step 2: Implement + pass + commit**

```bash
uv run pytest tests/test_findings_requests.py -v
git commit -am "feat: add finding review and client request lifecycle"
```

---

### Task 9: Working paper + Excel/PDF export

**Files:**
- Create: `apps/api/app/services/working_paper.py`, `apps/api/app/api/exports.py`, `apps/api/tests/test_exports.py`

**Interfaces:**
- Produces: `POST /runs/{id}/working-paper` → uses accepted/edited findings (+ optional AI narrative from Task 10); `GET /runs/{id}/export.xlsx`; `GET /runs/{id}/export.pdf`

- [ ] **Step 1: Failing export test**

```python
def test_excel_export_contains_summary_sheet(auth_client, reviewed_run):
    r = auth_client.get(f"/runs/{run_id}/export.xlsx")
    assert r.status_code == 200
    assert "spreadsheet" in r.headers["content-type"] or r.headers["content-type"].endswith("sheet")
```

- [ ] **Step 2: Implement**

Excel sheets: `Summary`, `Matches`, `Exceptions`, `Findings` (accepted/edited only).  
PDF via reportlab: title block, counts, exception list, “Prepared by: AI Assistant / Reviewed by: _____”.  
Export must not change finding statuses.

- [ ] **Step 3: Pass + commit**

```bash
uv run pytest tests/test_exports.py -v
git commit -am "feat: add working paper Excel and PDF exports"
```

---

### Task 10: Agno agents + AgentOS mount + enrich pipeline

**Files:**
- Create: `apps/api/app/ai/agents.py`, `apps/api/app/ai/workflow.py`, `apps/api/app/ai/schemas.py`, `apps/api/app/ai/enrich.py`, `apps/api/tests/test_ai_contracts.py`
- Modify: `apps/api/app/main.py`

**Interfaces:**
- Produces: AgentOS-wrapped `app`; `enrich_findings(run_id)` writes `ai_findings`; `draft_client_message(run_id) -> str`; `draft_working_paper_narrative(run_id) -> dict`  
- Agents: `explain-finding`, `draft-client-request`, `generate-working-paper` with `output_schema` Pydantic models  
- Workflow: function step `load_groups` → agent step explain (batched) — matching stays outside Agno

- [ ] **Step 1: Failing contract test with mocked model**

```python
def test_explain_output_schema_parses():
    from app.ai.schemas import ExplainFindingOut
    data = ExplainFindingOut(
        title="GSTIN mismatch — ABC Components",
        description="...",
        likely_reason="Supplier GSTIN differs between PR and 2B",
        recommended_action="Verify GSTIN on invoices",
        severity="high",
    )
    assert data.severity == "high"
```

- [ ] **Step 2: Define agents**

```python
# apps/api/app/ai/agents.py
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from app.ai.schemas import ExplainFindingOut, ClientRequestOut, WorkingPaperOut
from app.config import settings

def build_explain_agent() -> Agent:
    return Agent(
        id="explain-finding",
        name="ExplainFinding",
        model=OpenAIChat(id="gpt-4o-mini"),  # single cloud model; pin in config if needed
        output_schema=ExplainFindingOut,
        instructions=(
            "You explain GST reconciliation exception groups for Indian CAs. "
            "Use only the provided JSON evidence. Do not invent invoices or amounts."
        ),
    )
# similarly draft-client-request, generate-working-paper
```

- [ ] **Step 3: Mount AgentOS on FastAPI**

```python
# apps/api/app/main.py (final pattern)
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb  # or Postgres db adapter if configured
from app.ai.agents import build_explain_agent, build_client_request_agent, build_working_paper_agent

base_app = create_base_app()
# include all routers on base_app before wrap

agent_os = AgentOS(
    id="gst-workbench-os",
    description="CA GST reconciliation AgentOS",
    agents=[
        build_explain_agent(),
        build_client_request_agent(),
        build_working_paper_agent(),
    ],
    workflows=[build_enrich_workflow()],
    base_app=base_app,
)
app = agent_os.get_app()
```

Wire `enrich_findings` to call explain agent per group (or one workflow run) and insert `ai_findings` with `status=pending`. On LLM errors: log, set `ai_incomplete`, do not fail the whole recon.

- [ ] **Step 4: Mocked enrich integration test + commit**

```bash
uv run pytest tests/test_ai_contracts.py -v
git commit -am "feat: mount AgentOS and wire Agno explain/client/working-paper agents"
```

---

### Task 11: Next.js API client + auth screens + shell

**Files:**
- Create: `apps/web/src/lib/api.ts`, `apps/web/src/lib/auth.tsx`, `apps/web/src/app/login/page.tsx`, `apps/web/src/app/(app)/layout.tsx`, `apps/web/src/components/ui/*` (minimal shadcn)

**Interfaces:**
- Produces: token storage; login/signup/Google button; authenticated layout with nav (Dashboard, Clients)

- [ ] **Step 1: Implement `api.ts` fetch wrapper** with `Authorization: Bearer` and base URL `NEXT_PUBLIC_API_URL`.

- [ ] **Step 2: Login page** — email/password form + Google (Google Identity Services → `POST /auth/google`). Tripundra void canvas, ash pill CTA.

- [ ] **Step 3: Manual check** — signup → land on dashboard shell.

- [ ] **Step 4: Commit**

```bash
git add apps/web && git commit -m "feat: add web auth and app shell"
```

---

### Task 12: Dashboard + Clients + Client workspace UI

**Files:**
- Create: `apps/web/src/app/(app)/page.tsx`, `clients/page.tsx`, `clients/[id]/page.tsx`, components for activity list and document checklist

- [ ] **Step 1: Dashboard** — greeting by hour; four counts; recent activity links.

- [ ] **Step 2: Clients list + create dialog**.

- [ ] **Step 3: Workspace** — period selector, status chip, five-slot checklist from latest run, findings summary, buttons Upload / Review Findings.

- [ ] **Step 4: Commit**

```bash
git commit -am "feat: add dashboard, clients, and client workspace screens"
```

---

### Task 13: Upload UI + Review Findings UI (demo path)

**Files:**
- Create: `apps/web/src/app/(app)/clients/[id]/upload/page.tsx`, `clients/[id]/runs/[runId]/review/page.tsx`, components: `FindingCard`, `ClientRequestModal`, `ColumnMapper`

- [ ] **Step 1: Upload page** — five slots; template select or mapper UI saving profile; start run; poll `GET /runs/{id}` until `needs_review|failed`.

- [ ] **Step 2: Review page** — grouped findings; Accept / Edit / Dismiss; Generate client request (edit → approve → copy → mark sent); mark response received/resolved; Generate working paper + download Excel/PDF.

- [ ] **Step 3: End-to-end manual demo** with `fixtures/recon/tiny_pair` (and a larger fixture if available): two files → findings → message → export.

- [ ] **Step 4: Commit**

```bash
git commit -am "feat: add upload and review findings UI for demo path"
```

---

### Task 14: Metrics hooks + larger golden fixture + README pilot notes

**Files:**
- Create: `apps/api/app/services/metrics.py`, `apps/api/tests/test_metrics.py`, `fixtures/recon/medium_pair/`, update `README.md`

**Interfaces:**
- Produces: audit events `run_completed`, `finding_reviewed`, `export_downloaded`; helper computing accept+edit rate for an org; README with pilot checklist

- [ ] **Step 1: On finding PATCH and export, write `audit_logs`.**

- [ ] **Step 2: Add medium golden fixture (~100–200 rows) with expected summary; pytest marks `slow` optional.**

- [ ] **Step 3: README** — local run, env vars, demo script, “what we measure in pilot”, non-goals.

- [ ] **Step 4: Commit**

```bash
git commit -am "chore: add metrics hooks, medium fixture, and pilot README"
```

---

## Spec coverage checklist (self-review)

| Spec item | Task |
| --- | --- |
| Six screens | 11–13 |
| Auth email + Google, single-user org | 3 |
| All five document slots; bank store-only; sales stats; previous conditional | 5, 7 |
| Hybrid templates + mapper | 5 |
| Deterministic matching hierarchy + 8 outcomes | 6 |
| AI explains only; Agno + own AgentOS | 10 |
| Per-finding review gate | 8 |
| Client request response loop; pending = sent | 8, 4 |
| Working paper PDF/Excel | 9 |
| Dashboard counts | 4, 12 |
| Tripundra UI | 1, 11–13 |
| Metrics / pilot readiness | 14 |
| Non-goals excluded | Global constraints |

**Placeholder scan:** none intentional.  
**Type consistency:** `Invoice`, run statuses, finding statuses, and client_request statuses match the spec enums above across tasks.
