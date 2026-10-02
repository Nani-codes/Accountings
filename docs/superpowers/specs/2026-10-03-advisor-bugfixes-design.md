# Advisor & AgentOS Bug Fixes — Design

**Date:** 2026-10-03
**Status:** Approved pending user review
**Scope:** Fix 6 bugs introduced/exposed by the TallyPrime connector merge.

## Problem

After merging the TallyPrime hosted connector to `main` and reconstructing several
missing modules, the app runs but the Advisor feature is non-functional and the
build is broken. Six concrete bugs:

1. **(Critical) Org context never set.** `OrgContextMiddleware` decodes the JWT but
   has a `pass` where it must resolve the org. `get_request_org_id()` always returns
   `None`, so every `WorkbenchTools` / `TallyTools` call from the AgentOS Advisor
   returns the "unauthorized / sign in" error — even for authenticated users.
2. **(Critical) `/assistant` route 404.** Nav + README link to `/assistant` (the
   Advisor chat), but the page file does not exist. All API plumbing already exists
   in `apps/web/src/lib/api.ts`.
3. **AgentOS uses SQLite.** `build_agent_os()` hardcodes
   `SqliteDb(db_file="tmp/agent_os.db")`. Advisor session/run history should persist
   in the configured Postgres.
4. **`/health` route conflict.** AgentOS overrides the custom `/health` that reports
   `storage` + `tally_connector`. The custom health payload never reaches clients.
5. **Duplicate Operation ID warning.** `get_config` duplicate op-id in the OpenAPI
   schema (AgentOS components router). Cosmetic.
6. **(Critical) Typecheck broken.** `citations.ts` `ChatCitation` shape
   (`index/title/url/snippet`) does not match `api.ts` usage
   (`{ title: string | null; url: string }`). `npx tsc --noEmit` fails at
   `api.ts:137`.

## Approach

Minimal, root-cause fixes. No new abstractions.

### Fix 1 — Resolve org in middleware
`apps/api/app/api/middleware_org.py`: after decoding the JWT and reading `sub`,
open a short-lived DB session, look up `User.organization_id`, and
`set_request_org_id(user.organization_id)`. Reset to `None` in a `finally` after
the request to avoid context bleed across requests on reused worker threads.
Keep the broad `except` so unauthenticated requests still pass through with
`org_id=None` (tools then return the existing `_needs_auth()` message).

### Fix 2 — Build `/assistant` page
Create `apps/web/src/app/(app)/assistant/page.tsx` — a client component Advisor
chat UI that uses the **existing** helpers in `api.ts`:
`getMe`, `listAdvisorSessions`, `getAdvisorSessionRuns`, `runsToMessages`,
`runAdvisor`, `deleteAdvisorSession`. Features: session list (new/select/delete),
message thread (user/assistant), citations rendering, tool-name chips, file
attach, send box, loading state. Styling matches the existing Tripundra tokens
(`bg-void`, `text-ink`, `work-sheet`, `nav-link`, etc.) and the layout's
`isAdvisor` full-height mode. No new API functions needed.

### Fix 3 — AgentOS on Postgres
`apps/api/app/main.py`: replace `SqliteDb` with `PostgresDb` (import verified
available) using `settings.database_url`. Keep `AGENT_OS_DB_ID`. agno's
`PostgresDb` expects a `db_url`; strip the SQLAlchemy `+psycopg` driver suffix if
agno needs a plain URL (verify at implementation; fall back to passing the full
SQLAlchemy URL if accepted).

### Fix 4 — Custom `/health`
AgentOS registers its own `/health` on the shared app, overriding ours. README
documents `/health` as reporting storage + tally_connector, so we keep that
contract. **Decision:** after `app = agent_os.get_app()`, re-register the product
`/health` route on the final `app` so it wins. Extract the health handler into a
helper and attach it to whichever app object is returned (base or AgentOS).

### Fix 5 — Duplicate op-id
Originates in agno's components router (`get_config` vs `get_config_version`).
**Decision:** filter this specific `UserWarning` via `warnings.filterwarnings` at
import time in `main.py`. Do not patch agno internals. Cosmetic only.

### Fix 6 — Fix `ChatCitation` type
Rewrite `apps/web/src/lib/citations.ts` so `ChatCitation = { title: string | null;
url: string }` and `citationsFromWebSearchResult(result)` returns that shape
(parse web_search tool result JSON → `{ title, url }[]`), and `mergeCitations`
dedupes by `url`. Must make `npx tsc --noEmit` pass.

## Testing / Verification

- **Backend:** `uv run pytest` passes (existing tests for tally tools/pairing use
  direct `db`+`organization_id`, unaffected). Add a middleware unit test: a valid
  JWT sets `get_request_org_id()` to the user's org; a missing/invalid token sets
  `None`.
- **Frontend:** `npx tsc --noEmit` → 0 errors. `npm run build` succeeds.
  `/assistant` returns 200 and renders the chat shell.
- **Integration (manual):** Log in, open `/assistant`, send "list my clients" →
  Advisor returns client names (not the unauthorized message), proving Fix 1 + 2.
- **Health:** `/health` returns storage + tally_connector and 200 (override wins).

## Non-goals

- No streaming responses (uses `stream=false`, matching existing `runAdvisor`).
- No new AgentOS agents or tools.
- No redesign of existing pages.
