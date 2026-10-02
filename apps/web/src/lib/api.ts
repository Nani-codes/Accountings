import {
  citationsFromWebSearchResult,
  mergeCitations,
  type ChatCitation,
} from "@/lib/citations";

export type { ChatCitation };

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/** Must match apps/api/app/main.py AGENT_OS_DB_ID / CA_ADVISOR_AGENT_ID */
export const AGENT_OS_DB_ID = "gst-workbench-os-db";
export const CA_ADVISOR_AGENT_ID = "ca-advisor";

export type TokenResponse = { access_token: string; token_type: string };

export type MeResponse = {
  id: string;
  email: string;
  name: string;
  organization: { id: string; name: string };
};

function authHeaders(json = true): HeadersInit {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const headers: Record<string, string> = {};
  if (json) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function signup(body: {
  email: string;
  password: string;
  name: string;
  firm_name: string;
}): Promise<TokenResponse> {
  return api("/auth/signup", { method: "POST", body: JSON.stringify(body) });
}

export async function login(body: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  return api("/auth/login", { method: "POST", body: JSON.stringify(body) });
}

export async function getMe(): Promise<MeResponse> {
  return api<MeResponse>("/auth/me");
}

export function storeToken(token: string) {
  localStorage.setItem("access_token", token);
}

export function clearToken() {
  localStorage.removeItem("access_token");
}

export type OsSession = {
  session_id: string;
  session_name: string;
  created_at?: string | number | null;
  updated_at?: string | number | null;
  user_id?: string | null;
  agent_id?: string | null;
};

export type OsRun = {
  run_id?: string;
  session_id?: string;
  run_input?: string | null;
  content?: string | null;
  created_at?: string | number | null;
  citations?: {
    urls?: { title?: string | null; url?: string }[];
  } | null;
  tools?: {
    tool_name?: string;
    tool_args?: Record<string, unknown>;
    result?: string | null;
    tool_call_error?: boolean;
  }[];
  files?: { filename?: string | null; name?: string | null; mime_type?: string | null }[] | null;
  input_media?: {
    files?: { filename?: string | null; name?: string | null; mime_type?: string | null }[];
    images?: { filename?: string | null; name?: string | null; mime_type?: string | null }[];
  } | null;
};

export type ChatAttachment = {
  name: string;
  mime?: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  citations?: ChatCitation[];
  toolNames?: string[];
  attachments?: ChatAttachment[];
};

function qs(params: Record<string, string | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== "") sp.set(k, v);
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

function extractCitations(run: OsRun): ChatCitation[] {
  const fromModel: ChatCitation[] = [];
  const seen = new Set<string>();
  for (const item of run.citations?.urls || []) {
    const url = item?.url;
    if (!url || seen.has(url)) continue;
    seen.add(url);
    fromModel.push({ title: item.title ?? null, url });
  }
  const fromSearch: ChatCitation[] = [];
  for (const tool of run.tools || []) {
    if (tool.tool_name !== "web_search") continue;
    fromSearch.push(...citationsFromWebSearchResult(tool.result));
  }
  // Prefer search-result order for [1]/[n] markers; keep model citations as extras.
  return mergeCitations(fromSearch, fromModel);
}

function attachmentName(item: {
  filename?: string | null;
  name?: string | null;
  mime_type?: string | null;
}): ChatAttachment | null {
  const name = (item.filename || item.name || "").trim();
  if (!name) return null;
  return { name, mime: item.mime_type ?? undefined };
}

function extractRunAttachments(run: OsRun): ChatAttachment[] {
  const out: ChatAttachment[] = [];
  const seen = new Set<string>();
  const candidates = [
    ...(run.input_media?.files ?? []),
    ...(run.input_media?.images ?? []),
    ...(run.files ?? []),
  ];
  for (const item of candidates) {
    const att = attachmentName(item);
    if (!att || seen.has(att.name)) continue;
    seen.add(att.name);
    out.push(att);
  }
  return out;
}

export async function listAdvisorSessions(
  userId: string,
): Promise<OsSession[]> {
  const path =
    `/sessions` +
    qs({
      type: "agent",
      component_id: CA_ADVISOR_AGENT_ID,
      user_id: userId,
      db_id: AGENT_OS_DB_ID,
      limit: "50",
      sort_by: "updated_at",
      sort_order: "desc",
    });
  const res = await api<{ data: OsSession[] }>(path);
  return res.data ?? [];
}

export async function getAdvisorSessionRuns(
  sessionId: string,
  userId: string,
): Promise<OsRun[]> {
  const path =
    `/sessions/${encodeURIComponent(sessionId)}/runs` +
    qs({
      type: "agent",
      user_id: userId,
      db_id: AGENT_OS_DB_ID,
    });
  const res = await api<OsRun[] | { data: OsRun[] }>(path);
  if (Array.isArray(res)) return res;
  return res.data ?? [];
}

export function runsToMessages(runs: OsRun[]): ChatMessage[] {
  const messages: ChatMessage[] = [];
  for (const run of runs) {
    const input = (run.run_input ?? "").trim();
    const attachments = extractRunAttachments(run);
    if (input || attachments.length) {
      messages.push({
        role: "user",
        content: input || "Please review the attached document(s).",
        attachments: attachments.length ? attachments : undefined,
      });
    }
    const content =
      typeof run.content === "string"
        ? run.content
        : run.content != null
          ? String(run.content)
          : "";
    const toolNames = [
      ...new Set(
        (run.tools ?? [])
          .map((t) => t.tool_name)
          .filter((n): n is string => Boolean(n)),
      ),
    ];
    if (content || toolNames.length) {
      messages.push({
        role: "assistant",
        content,
        citations: extractCitations(run),
        toolNames,
      });
    }
  }
  return messages;
}

export async function deleteAdvisorSession(
  sessionId: string,
  userId: string,
): Promise<void> {
  const path =
    `/sessions/${encodeURIComponent(sessionId)}` +
    qs({
      user_id: userId,
      db_id: AGENT_OS_DB_ID,
    });
  await api<void>(path, { method: "DELETE" });
}

export type AdvisorRunResult = {
  session_id: string;
  reply: string;
  citations: ChatCitation[];
  toolNames: string[];
};

/** Create/continue a ca-advisor turn via AgentOS POST /agents/{id}/runs */
export async function runAdvisor(
  message: string,
  opts: {
    sessionId?: string | null;
    userId: string;
    files?: File[];
  },
): Promise<AdvisorRunResult> {
  const form = new FormData();
  form.append("message", message);
  form.append("stream", "false");
  form.append("user_id", opts.userId);
  if (opts.sessionId) form.append("session_id", opts.sessionId);
  for (const file of opts.files ?? []) {
    form.append("files", file, file.name);
  }

  const res = await fetch(
    `${API_URL}/agents/${CA_ADVISOR_AGENT_ID}/runs`,
    {
      method: "POST",
      headers: authHeaders(false),
      body: form,
    },
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  const body = (await res.json()) as OsRun & {
    session_id?: string;
    content?: unknown;
  };
  const reply =
    typeof body.content === "string"
      ? body.content
      : body.content != null
        ? String(body.content)
        : "";
  const toolNames = [
    ...new Set(
      (body.tools ?? [])
        .map((t) => t.tool_name)
        .filter((n): n is string => Boolean(n)),
    ),
  ];
  return {
    session_id: body.session_id || opts.sessionId || "",
    reply,
    citations: extractCitations(body),
    toolNames,
  };
}

export type TallyStatus = {
  status: "not_connected" | "offline" | "online" | "tally_unreachable" | string;
  device_label?: string | null;
  last_seen_at?: string | null;
  last_tally_ok_at?: string | null;
};

export async function getTallyStatus(): Promise<TallyStatus> {
  return api("/tally/status");
}

export async function createTallyPairing(): Promise<{
  code: string;
  expires_at: string;
  download_url?: string | null;
}> {
  return api("/tally/pairing", { method: "POST" });
}

export async function disconnectTally(): Promise<void> {
  await api("/tally/disconnect", { method: "POST" });
}
