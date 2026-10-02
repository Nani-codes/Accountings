# TallyPrime Hosted Connector — Design Spec

**Date:** 2026-10-03  
**Product:** Accountings AI GST workbench (CA Advisor)  
**Goal:** Let non-technical CA firms connect TallyPrime so Advisor can answer book questions — without firms hosting MCP or exposing ports.  
**Worktree:** `.worktrees/ai-gst-mvp`

## 1. Problem & success

CAs keep books in TallyPrime on a firm PC. Advisor today only sees uploaded Excel and workbench data. Live Tally lookups (ledgers, day book, trial balance) need a path that:

1. **We host** the integration (gateway + Advisor tools).
2. The firm only **connects** with a simple pairing flow.
3. Stays **read-only** and **org-scoped**.

**Demo bar:**

> Settings → Connect Tally → download Windows connector → paste pairing code → status Online → ask Advisor “What’s the balance of …?” and get a Tally-backed answer.

**Primary trust metric:** Advisor never invents Tally numbers when the connector is offline; it clearly says how to reconnect.

## 2. Decisions locked in brainstorming

| Topic | Decision |
| --- | --- |
| Reachability | Firm-side **Accountings Connector** dials out (WebSocket); no inbound ports |
| Hosting | Cloud hosts Tally gateway; firms do **not** run MCP |
| Advisor integration | Org-scoped **`TallyTools`** (same pattern as `WorkbenchTools`), not env-based firm MCP URL |
| Access mode | **Read-only** whitelist |
| Company scope (v1) | Whatever company is open in TallyPrime; no per-client company map yet |
| Connector OS (v1) | **Windows** only |
| UX | Settings → Tally: pairing code, download, Online/Offline/Not connected, Disconnect |

## 3. Explicit non-goals (v1)

- Write / post vouchers or any mutating Tally XML
- Per-client ↔ Tally company mapping
- macOS / Linux connector
- Hosted MCP for third-party clients (optional later; not required for Advisor)
- Using Tally as reconciliation source of truth (uploads remain primary for recon)
- Auto-configuring Tally XML gateway on the firm PC
- Multi-connector load balancing per org (one active device is enough)

## 4. Architecture

```text
CA browser                         Firm Windows PC
  Settings → Tally                   Accountings Connector
  Advisor (TallyTools)                  │
         │                              ├─ local HTTP → TallyPrime XML (:9000)
         ▼                              └─ outbound WSS → cloud
FastAPI + AgentOS
  /api/tally/*  (pair, status, revoke, connector WS)
  Tally gateway (whitelisted read ops only)
  tally_connections + pairing codes (DB)
```

### Boundaries

| Piece | Owns |
| --- | --- |
| **Next.js Settings → Tally** | Pairing UI, download CTA, status, disconnect |
| **FastAPI `/api/tally/*`** | Pairing codes, connection records, connector WebSocket, status for UI |
| **Tally gateway** | Named read-only ops → XML templates → parse → JSON; reject unknown ops |
| **`TallyTools`** | Advisor-facing tools; resolve `organization_id` from request JWT (same as Workbench) |
| **Connector** | Pair with code → store device token → keep WSS alive → proxy gateway requests to local Tally |
| **Agent instructions** | Use Tally tools when connected; never show internal IDs; explain offline clearly |

### Hard rules

1. The LLM never sends raw XML. Only named tools with structured args.
2. Gateway never executes write/import/alter Tally requests.
3. Every relay hop is bound to `organization_id` from the authenticated connector session.
4. Replace (do not keep) the firm-URL `TALLY_MCP_*` / `tally_mcp.py` “point AgentOS at firm MCP” model for Advisor.

## 5. Connect flow (non-technical)

1. CA opens **Settings → Tally**.
2. Clicks **Connect Tally** → API creates a short-lived **pairing code** (~15 minutes) and shows **Download connector**.
3. CA installs connector on the firm PC where TallyPrime runs.
4. Connector prompts for the code (or opens a deep link), exchanges it for a **device token**, opens WSS to `/api/tally/connector/ws`.
5. Connector probes `http://127.0.0.1:9000` (default; advanced host/port override hidden behind “Advanced”).
6. UI shows **Online** when an authenticated connector has a fresh heartbeat and Tally probe succeeds.
7. **Disconnect** revokes the device token; connector is rejected until re-paired.

Statuses:

| Status | Meaning |
| --- | --- |
| `not_connected` | No active/revoked connection for org |
| `offline` | Paired, but no live WSS / stale heartbeat |
| `online` | Live WSS + recent successful Tally probe |
| `tally_unreachable` | Connector online but local Tally XML port failed |

## 6. Data model

### `tally_connections`

| Column | Notes |
| --- | --- |
| `id` | UUID PK |
| `organization_id` | FK → organizations, unique among non-revoked rows (one primary device v1) |
| `device_id` | Stable id generated at pair time |
| `token_hash` | Hash of device bearer token (never store plaintext) |
| `label` | Optional friendly name (e.g. hostname) |
| `status` | `paired` \| `revoked` |
| `last_seen_at` | Updated on heartbeat |
| `last_tally_ok_at` | Updated when local Tally probe succeeds |
| `tally_host` | Reported by connector (default 127.0.0.1) |
| `tally_port` | Reported by connector (default 9000) |
| `created_at` / `revoked_at` | Timestamps |

### `tally_pairing_codes`

| Column | Notes |
| --- | --- |
| `id` | UUID PK |
| `organization_id` | FK |
| `code_hash` | Hash of user-facing code |
| `expires_at` | ~15 minutes |
| `consumed_at` | Set when exchanged for device token |
| `created_at` | Timestamp |

Pairing codes are single-use. Creating a new code does not immediately revoke an existing connection; **Disconnect** does.

## 7. API surface

Authenticated (JWT / org context) — CA app:

- `POST /api/tally/pairing` → `{ code, expires_at, download_url }`
- `GET /api/tally/status` → `{ status, device_label?, last_seen_at?, last_tally_ok_at? }`
- `POST /api/tally/disconnect` → revoke connection + invalidate token

Connector (device token after pair):

- `POST /api/tally/connector/pair` → body `{ code }` → `{ device_id, device_token, ws_url }`
- `GET|WS /api/tally/connector/ws` → Authorization: device bearer; heartbeat + request/response frames

Relay frame shape (illustrative):

```json
{ "type": "request", "id": "...", "op": "ledger_balance", "args": { "ledger": "…", "from": "…", "to": "…" } }
{ "type": "response", "id": "...", "ok": true, "data": { } }
{ "type": "heartbeat", "tally_ok": true }
```

## 8. `TallyTools` (Advisor)

Always registered on CA Advisor (like Workbench). Tools fail soft with actionable messages when not online.

| Tool | Purpose |
| --- | --- |
| `tally_connection_status` | Online / offline / not connected / tally unreachable |
| `tally_list_companies` | Companies visible / current open company if exposed by Tally |
| `tally_ledger_balance` | Balance for a ledger over optional period |
| `tally_day_book` | Day book for a date or range (bounded size) |
| `tally_trial_balance` | Trial balance for a period (summary) |

Implementation: resolve org → find live connector session → send whitelisted `op` → wait with timeout → return parsed JSON (no UUIDs in human-facing payloads).

Agent instructions: prefer Tally tools for live book questions when status is online; never claim Tally data when offline; never expose device tokens or internal connection ids.

## 9. Security

- Pairing codes expire and are single-use; store only hashes.
- Device tokens are high-entropy; store only hashes; send only once at pair.
- Connector initiates outbound WSS only.
- Org isolation on pair, WS session, and every tool relay.
- Gateway allowlist of ops; reject unknown / write-like requests.
- Timeouts and max response size on relay to protect Advisor latency.
- Download URL for connector is product-controlled (release artifact), not user-uploaded binaries.

## 10. Migration from current code

Remove Advisor dependency on:

- `TALLY_MCP_ENABLED` / `TALLY_MCP_URL` / `TALLY_MCP_COMMAND` / `TALLY_MCP_AUTH_TOKEN`
- `app/ai/tally_mcp.py` firm-MCP `MCPTools` attachment
- README / `.env.example` “point at firm MCP” instructions

Replace with Tally gateway + `TallyTools` + Settings UI + connector app package under e.g. `apps/tally-connector/`.

## 11. Testing

- **Unit:** pairing consume/expiry; disconnect revokes; gateway rejects non-whitelist ops; tools return clear errors when no session.
- **Integration:** fake in-process connector session → `tally_ledger_balance` returns fixture payload.
- **Manual:** Windows + TallyPrime XML on :9000 → full connect → Advisor question.

## 12. Rollout notes

- Recon and uploads remain unchanged and primary.
- Feature is usable only when connector is Online; otherwise Advisor degrades gracefully.
- Later: hosted MCP façade over the same gateway; per-client company mapping; write ops with explicit confirmation.
