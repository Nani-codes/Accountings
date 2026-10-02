# AI GST Reconciliation MVP — Design Spec

**Date:** 2026-10-02  
**Product wedge:** AI GST Reconciliation & Client Follow-up for CA Firms  
**Horizon:** Ship in 2–4 weeks; architecture leaves a path to a full CA AI OS  
**Repo:** greenfield (`Accountings`); UI language follows Trilolabs Tripundra Clarity (`DESIGN.md`)

## 1. Problem & success

Chartered Accountants spend hours reconciling purchase registers against GSTR-2B in Excel. The MVP proves that a CA will upload real GST data, trust AI-assisted explanations of exceptions, generate client follow-ups, and reuse the product monthly.

**Demo bar (first working version):**

> Upload two Excel files → ~30 seconds → ~1,000 invoices reconciled → ~20 exceptions grouped into ~5 understandable issues → open evidence → generate a client message → export the working paper.

**Primary trust metric:** % of AI findings Accepted or Edited (vs Dismissed).

## 2. Explicit non-goals (v1)

Not in scope:

- GST / Income Tax / TDS / MCA filing
- Tally (or other ERP) live integrations
- WhatsApp / email send APIs
- Billing / Stripe / subscription enforcement
- CRM or practice management
- Mobile app
- Multi-user orgs and fine-grained roles
- Autonomous multi-agent matching or autonomous filing
- Self-host / firm-local deploy (architecture may allow later; pilot is single cloud SaaS)

## 3. Decisions locked in brainstorming

| Topic | Decision |
| --- | --- |
| Document slots | All five active: Purchase, GSTR-2B, Sales, Previous recon (optional), Bank Statement |
| Matching scope | Purchase Register ↔ GSTR-2B only |
| Column mapping | Hybrid: 2–3 built-in templates + manual mapper; save profile per client/doc type; no AI column guessing |
| Tenancy | Single user per organization |
| Non-match docs | Sales: normalize + stats; Previous: parse if our export format else store; Bank: store + checklist only |
| Auth | Email/password + Google OAuth |
| Deploy | Single cloud SaaS |
| LLM | One cloud model (no fallback in v1) |
| Agno | Fuller stack: Workflows + Agents on **own AgentOS**; no autonomous matching |
| Client requests | Persisted + response loop (Draft → Approved → Sent → Response received / Resolved); no WhatsApp |
| Review gate | Per-finding: Accepted / Edited / Dismissed before inclusion in client request or working paper |
| Build shape | **Approach A + own AgentOS:** monolith FastAPI (product API + recon in-process) + thin Next.js; AgentOS as Agno control plane |

## 4. Architecture

```text
Next.js (6 screens, Tripundra Operate density)
        │
        ▼
FastAPI (auth, clients, uploads, domain API, exports)
        │
        ├── PostgreSQL (source of truth for domain data)
        ├── S3-compatible object storage (Excel/PDF)
        ├── Deterministic reconciliation engine (in-process Python)
        └── Agno Workflows / Agents
                    │
                    ▼
              Own AgentOS
           (run ops, later CA AI OS growth)
```

### Boundaries

**FastAPI owns:** authentication, organizations/users, clients, document uploads, `reconciliation_run` lifecycle, invoices/results, finding review states, client requests, audit logs, PDF/Excel export rendering.

**Reconciliation engine owns:** parse (templates + mapper), normalize to `Invoice`, matching hierarchy, exception categorization. **No LLM** in this path.

**Agno on AgentOS owns:** exception grouping explanation, client-request draft, working-paper narrative. Triggered by FastAPI after deterministic success, and on demand for message/working paper.

**Next.js owns:** UI only — Login, Firm Dashboard, Clients, Client Workspace, Upload, Review Findings.

### Hard rule

Python does arithmetic and matching. The LLM receives only pre-grouped exception bundles and returns structured explanations. Agents never invent match rules or call tools against full ledgers.

## 5. Screens

### ① Login

Email/password and Google. First signup creates a single-user organization.

### ② Firm Dashboard

Greeting; counts: Clients, Active GST reviews, Exceptions, Client responses pending (`client_requests` in `sent` awaiting response); recent activity list. No overbuilt widgets.

### ③ Clients

List + create. Service chips (e.g. GST) and GST review status. Click opens workspace.

### ④ Client workspace

Client name, period (e.g. March 2026), status, document checklist (five slots), AI findings summary (ITC exposure, mismatch counts), CTA **Review Findings**.

### ⑤ Upload

Slots for Purchase Register, GSTR-2B, Sales Register, Previous reconciliation (optional), Bank Statement. Template select or column mapper. Starts or continues a `reconciliation_run`. Excel/CSV first; GSTR-2B also accepts JSON where practical.

### ⑥ Review Findings

Grouped findings with evidence; Accept / Edit / Dismiss; Generate client request; Generate working paper; export PDF and Excel.

## 6. Reconciliation engine

### Normalized invoice

```text
Invoice {
  invoice_number
  invoice_date
  supplier_gstin
  recipient_gstin
  taxable_value
  igst, cgst, sgst, cess
  total
}
```

### Matching hierarchy (deterministic)

1. GSTIN + invoice number  
2. GSTIN + invoice number normalization  
3. GSTIN + amount + date  
4. GSTIN + approximate amount  
5. Fuzzy matching  

### Match / exception outcomes (8)

1. Exact match (successful match; not an actionable exception)  
2. Invoice missing in 2B  
3. GSTIN mismatch  
4. Amount mismatch  
5. Tax mismatch  
6. Duplicate  
7. Date mismatch (beyond configurable threshold)  
8. Credit/debit note mismatch (simple v1 treatment)

Actionable `ai_findings` are produced for outcomes 2–8 (grouped). Exact matches contribute to summary counts only.

Sales invoices are stored/normalized for stats and future work; they are **not** matched to 2B in v1.

## 7. AI pipeline (Agno)

Controlled workflow (not autonomous agents):

```text
Files → Parser → Normalizer → Deterministic reconciliation
  → Exception grouping (Python)
  → LLM explanation (Agno Agent) → structured ai_findings
  → CA per-finding review
  → (on demand) DraftClientRequest / GenerateWorkingPaper
```

### Agents / contracts

- **ExplainFinding** — input: grouped exception JSON; output: title, description, likely_reason, recommended_action, severity.  
- **DraftClientRequest** — input: accepted/edited findings only; output: editable email-style body.  
- **GenerateWorkingPaper** — input: run summary + accepted/edited findings; output: structured narrative; FastAPI renders PDF/Excel.

LLM failure after a successful match leaves deterministic results usable; findings may be empty/partial with retry.

## 8. Data model

### Tables

`organizations`, `users`, `clients`, `client_documents`, `column_mapping_profiles`, `reconciliation_runs`, `invoices`, `reconciliation_results`, `ai_findings`, `client_requests`, `audit_logs`.

### `reconciliation_run`

`id`, `client_id`, `period`, document references, `status`, `started_at`, `completed_at`, `summary` (JSON counts/totals), error info if failed.

**Statuses:** `draft` → `uploading` → `parsing` → `reconciling` → `ai_enriching` → `needs_review` → `reviewed` | `failed`.

A run enters `needs_review` when deterministic recon (and AI enrichment, if attempted) finishes. It becomes `reviewed` only when **every** finding is `accepted`, `edited`, or `dismissed` (no `pending` left). Client request and working paper may be generated earlier, but they **include only** `accepted` / `edited` findings; `pending` and `dismissed` are excluded.

### `reconciliation_result`

`run_id`, `purchase_invoice_id`, `gstr_invoice_id`, `match_status`, `match_score`, `difference_amount`, `difference_type`.

### `ai_finding`

`client_id`, `run_id`, `category`, `severity`, `title`, `description`, `evidence` (JSON), `recommended_action`, `status` ∈ `pending | accepted | edited | dismissed`.

### `client_request`

Linked finding IDs, body, `status` ∈ `draft | approved | sent | response_received | resolved`, optional CA note on response/resolve.

**Dashboard “Client responses pending”:** count of requests in `sent` awaiting response.

### Column mapping profiles

Per `client_id` + document type; reused across periods after first hybrid map.

## 9. Auth, storage, UI system

- **Auth:** email/password + Google OAuth; one user per org in v1 (schema may keep `organization_id` for future multi-user).  
- **DB:** PostgreSQL.  
- **Files:** S3-compatible object storage.  
- **Excel:** pandas + openpyxl.  
- **Frontend:** Next.js, Tailwind, shadcn/ui, TanStack Query; Tripundra Operate density (void/ash/Shiva blue, Manrope).  
- **AI:** single cloud model via Agno on own AgentOS.

## 10. Error handling

- Parse / mapping errors: stay on Upload with actionable messages; do not advance to reconciling.  
- Recon engine failure: run → `failed`; retry from last good stage when safe.  
- AI enrichment failure: keep match results; mark findings incomplete; allow retry of AI step.  
- Export failure: do not mutate finding/request statuses.

## 11. Testing

- **Unit:** normalization, invoice-number cleanup, each match tier, each exception category, amount/tax diffs.  
- **Golden fixtures:** anonymized Purchase + 2B pairs with expected match/exception counts.  
- **API:** upload → run lifecycle → finding transitions → client_request state machine → exports.  
- **AI:** mocked LLM schema contract tests; optional one live smoke.  
- No WhatsApp/email E2E; no multi-role tests in v1.

## 12. Metrics & pilot

**Metrics from day one:** time-to-reviewed/export (plus optional self-reported baseline), match accuracy vs fixtures/pilot tags, runs/firm/month, clients/firm, files uploaded, finding accept+edit rate.

**Pilot (week 4):** 5–10 CA firms on shared cloud SaaS; authorized/anonymized real data; manual pricing conversations (no billing product); false-positive pass before scope expansion. North-star learning goal: path to 10 paying firms.

## 13. Four-week plan

| Week | Focus |
| --- | --- |
| 1 | Auth, org, clients, upload, hybrid mapper, DB, dashboard shell, AgentOS wired |
| 2 | Normalizer, matching engine, exceptions, results UI |
| 3 | Agno explain / client request / working paper + per-finding review gates |
| 4 | Pilot, false-positive fixes, UX polish |

## 14. Growth path (post-MVP, not v1 build)

GST wedge → Client Intelligence → Audit → Tax → Full CA AI OS.  
Later: multi-user/roles, billing, integrations, dual-model/local privacy, worker extraction if in-process load demands it, richer AgentOS multi-agent workflows **still without** LLM-owned arithmetic.

## 15. Pitch language

Do not lead with “AI SaaS for Chartered Accountants.” Lead with:

> **AI GST Reconciliation & Client Follow-up for CA Firms**  
> Upload GST data. Find mismatches automatically. Understand why. Generate client requests. Finish the review faster.
