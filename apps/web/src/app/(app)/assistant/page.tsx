"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  getMe,
  listAdvisorSessions,
  getAdvisorSessionRuns,
  runsToMessages,
  runAdvisor,
  deleteAdvisorSession,
  type ChatMessage,
  type OsSession,
} from "@/lib/api";

export default function AssistantPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<OsSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auth guard + bootstrap user and session list.
  useEffect(() => {
    if (typeof window !== "undefined" && !localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const me = await getMe();
        setUserId(me.id);
        const list = await listAdvisorSessions(me.id);
        setSessions(list);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load Advisor");
      }
    })();
  }, [router]);

  // Auto-scroll to the latest message.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, sending]);

  const refreshSessions = useCallback(async () => {
    if (!userId) return;
    try {
      setSessions(await listAdvisorSessions(userId));
    } catch {
      // non-fatal
    }
  }, [userId]);

  async function openSession(id: string) {
    if (!userId || id === sessionId) return;
    setLoadingHistory(true);
    setError(null);
    try {
      const runs = await getAdvisorSessionRuns(id, userId);
      setMessages(runsToMessages(runs));
      setSessionId(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load conversation");
    } finally {
      setLoadingHistory(false);
    }
  }

  function newSession() {
    setSessionId(null);
    setMessages([]);
    setInput("");
    setFiles([]);
    setError(null);
  }

  async function removeSession(id: string) {
    if (!userId) return;
    try {
      await deleteAdvisorSession(id, userId);
      if (id === sessionId) newSession();
      await refreshSessions();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete conversation");
    }
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if ((!text && files.length === 0) || sending || !userId) return;

    const attachments = files.map((f) => ({ name: f.name, mime: f.type }));
    const userMsg: ChatMessage = {
      role: "user",
      content: text || "Please review the attached document(s).",
      attachments: attachments.length ? attachments : undefined,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    const sentFiles = files;
    setFiles([]);
    setSending(true);
    setError(null);

    try {
      const result = await runAdvisor(text, {
        sessionId,
        userId,
        files: sentFiles,
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.reply,
          citations: result.citations,
          toolNames: result.toolNames,
        },
      ]);
      if (!sessionId && result.session_id) {
        setSessionId(result.session_id);
      }
      await refreshSessions();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Advisor request failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-5xl gap-0 sm:gap-4 sm:px-4">
      {/* Session sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-line py-4 pr-3 sm:flex">
        <button
          type="button"
          onClick={newSession}
          className="btn-secondary mb-3 w-full text-sm"
        >
          + New chat
        </button>
        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {sessions.length === 0 && (
            <p className="px-2 text-xs text-ink-faint">No conversations yet.</p>
          )}
          {sessions.map((s) => (
            <div
              key={s.session_id}
              data-active={s.session_id === sessionId}
              className="group flex items-center justify-between gap-1 rounded-lg px-2 py-1.5 text-sm hover:bg-void-elevated data-[active=true]:bg-void-elevated"
            >
              <button
                type="button"
                onClick={() => openSession(s.session_id)}
                className="min-w-0 flex-1 truncate text-left text-ink-muted hover:text-ink"
              >
                {s.session_name || "Untitled"}
              </button>
              <button
                type="button"
                aria-label="Delete conversation"
                onClick={() => removeSession(s.session_id)}
                className="shrink-0 text-ink-faint opacity-0 transition hover:text-stamp group-hover:opacity-100"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Chat column */}
      <div className="flex min-h-0 flex-1 flex-col py-4">
        <header className="mb-3 shrink-0">
          <h1 className="text-lg font-semibold tracking-tight text-ink">
            Advisor
          </h1>
          <p className="text-xs text-ink-muted">
            Ask about clients, reconciliation runs, findings, or live Tally data.
          </p>
        </header>

        <div
          ref={scrollRef}
          className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1"
        >
          {loadingHistory && (
            <p className="text-sm text-ink-faint">Loading conversation…</p>
          )}
          {!loadingHistory && messages.length === 0 && (
            <div className="rounded-panel border border-line bg-void-elevated p-6 text-sm text-ink-muted">
              <p className="mb-2 font-medium text-ink">Try asking:</p>
              <ul className="list-inside list-disc space-y-1">
                <li>“List my clients”</li>
                <li>“Show reconciliation findings for Acme for 2025-04”</li>
                <li>“What’s the ledger balance for Acme in Tally?”</li>
              </ul>
            </div>
          )}
          {messages.map((m, i) => (
            <MessageBubble key={i} message={m} />
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="rounded-panel bg-void-elevated px-3 py-2 text-sm text-ink-faint">
                Advisor is thinking…
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="mt-3 shrink-0 rounded-panel border border-stamp bg-stamp/10 px-3 py-2 text-sm text-stamp">
            {error}
          </div>
        )}

        {/* Composer */}
        <form onSubmit={handleSend} className="mt-3 shrink-0 space-y-2">
          {files.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {files.map((f, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 rounded-full bg-void-elevated px-2 py-0.5 text-xs text-ink-muted"
                >
                  {f.name}
                  <button
                    type="button"
                    aria-label="Remove file"
                    onClick={() =>
                      setFiles((prev) => prev.filter((_, idx) => idx !== i))
                    }
                    className="text-ink-faint hover:text-stamp"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex items-end gap-2">
            <label className="btn-secondary cursor-pointer px-3 py-2 text-sm">
              Attach
              <input
                type="file"
                multiple
                className="hidden"
                onChange={(e) =>
                  setFiles((prev) => [
                    ...prev,
                    ...Array.from(e.target.files ?? []),
                  ])
                }
              />
            </label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSend(e as unknown as FormEvent);
                }
              }}
              rows={1}
              placeholder="Message Advisor…"
              className="min-h-10 flex-1 resize-none rounded-xl border border-line bg-void-elevated px-3 py-2 text-sm text-ink outline-none focus:border-ink-faint"
            />
            <button
              type="submit"
              disabled={sending || (!input.trim() && files.length === 0)}
              className="btn-primary px-4 py-2 text-sm disabled:opacity-60"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-panel px-3 py-2 text-sm ${
          isUser
            ? "bg-cta text-cta-ink"
            : "border border-line bg-void-elevated text-ink"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{message.content}</p>

        {message.attachments && message.attachments.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {message.attachments.map((a, i) => (
              <span
                key={i}
                className="inline-flex rounded-full bg-void/20 px-2 py-0.5 text-xs"
              >
                {a.name}
              </span>
            ))}
          </div>
        )}

        {message.toolNames && message.toolNames.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {message.toolNames.map((t, i) => (
              <span
                key={i}
                className="inline-flex rounded-full bg-void-elevated px-2 py-0.5 text-[10px] uppercase tracking-wide text-ink-faint ring-1 ring-line"
              >
                {t}
              </span>
            ))}
          </div>
        )}

        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 space-y-1 border-t border-line pt-2">
            {message.citations.map((c, i) => (
              <a
                key={i}
                href={c.url}
                target="_blank"
                rel="noreferrer"
                className="block truncate text-xs text-ink-muted underline hover:text-ink"
              >
                [{i + 1}] {c.title || c.url}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
