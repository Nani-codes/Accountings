# CA Advisor Chatbot — Design

**Date:** 2026-10-02  
**Status:** Approved for implementation  
**Parent:** AI GST Reconciliation MVP

## Goal

Firm-wide assistant where a CA can:

1. Clarify GST / process doubts grounded via **Vertex Google Search** with citations (prefer official government sources; open web as fallback).
2. Ask about **live workbench data** (clients, runs, findings, invoices) with org-scoped, read-only tools.

## Locked decisions

| Topic | Choice |
|-------|--------|
| Shape | Single Agno agent `ca-advisor` on existing AgentOS (Approach 1) |
| Grounding | Gemini `search=True` (Google Search + citations); no custom domain allowlist for MVP |
| Source preference | Instructions prefer official/gov (e.g. gst.gov.in, cbic.gov.in); open web fallback |
| Knowledge base | No local PDF corpus / in-app uploads for MVP |
| Data access | Read-only tools over Postgres, scoped by JWT `organization_id` |
| Writes | None (no accept/dismiss, email, uploads) |
| UI | Global `/assistant` page + header nav |

## Architecture

```
Next.js /assistant  →  POST /api/chat (JWT)  →  Agno ca-advisor
                                              ├─ Gemini search=True → citations
                                              └─ WorkbenchTools (org-scoped) → Postgres
                                              └─ SqliteDb sessions (AgentOS / chat history)
```

Product chat always goes through JWT-authenticated FastAPI. AgentOS registers the same agent for control-plane visibility; org tools are bound per chat request so the model never chooses an `organization_id`.

## Components

### Agent (`ca-advisor`)

- Same Vertex project/model stack as explain/client/working-paper agents.
- `search=True` on Gemini for live web grounding.
- Instructions: Indian CA assistant; prefer official sources; use tools before inventing workbench facts; never invent GSTINs/amounts/invoices; educational only — verify before filing.

### Tools (read-only, org-scoped)

| Tool | Purpose |
|------|---------|
| `list_clients` | id, name, gstin |
| `get_client` | client + recent runs summary |
| `list_runs` | filter by client_id / status |
| `get_run` | period, status, counts, upload slots |
| `list_findings` | type, severity, review status, short text |
| `get_finding` | full finding + evidence snippet |
| `search_invoices` | by invoice number / GSTIN within a run |

`organization_id` is closed over from the authenticated user; tools must not accept org id from the model.

### API

`POST /api/chat`

Request: `{ "message": string, "session_id"?: string }`  
Response: `{ "session_id": string, "reply": string, "citations": [{ "title"?: string, "url": string }] }`

- Auth required (same JWT as rest of product).
- Sessions keyed by `user_id` + `session_id`; history via Agno db.
- Vertex unavailable → clear 503-style error (no fabricated legal answer).

### UI

- `/assistant`: message list, composer, new chat, citation links, disclaimer on empty state.
- Header link: Assistant.

## Errors & safety

- Cross-org isolation enforced in every tool query.
- Unknown client/run → structured not-found for the agent (no guessing).
- Disclaimer: educational; verify against official sources before filing.

## Testing

- Unit: tools return only org A data when org B rows exist.
- Contract: chat requires auth; response schema includes `session_id`, `reply`, `citations`.
- Smoke (credentials present): legal question yields citations; named-client question uses tools.

## Out of scope (MVP)

Domain allowlist enforcement, uploaded knowledge base, streaming polish, write actions, Slack/WhatsApp, autonomous filing advice.

## Success criteria

- CA asks a GST process question → answer with source links.
- CA asks about a named client/run/finding → accurate org-scoped workbench data.
