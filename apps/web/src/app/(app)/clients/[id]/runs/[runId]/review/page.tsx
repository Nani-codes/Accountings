"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";

type Finding = {
  id: string;
  title: string;
  description: string;
  category: string;
  severity: string;
  recommended_action: string;
  status: string;
  evidence: Record<string, unknown>;
};

type ClientRequest = {
  id: string;
  body: string;
  status: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function ReviewPage() {
  const { id, runId } = useParams<{ id: string; runId: string }>();
  const router = useRouter();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [request, setRequest] = useState<ClientRequest | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const rows = await api<Finding[]>(`/runs/${runId}/findings`);
    setFindings(rows);
  }

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    load().catch((e) => setError(e.message));
  }, [runId, router]);

  async function setStatus(findingId: string, status: string) {
    await api(`/findings/${findingId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    await load();
  }

  async function generateRequest() {
    setError(null);
    try {
      const req = await api<ClientRequest>(`/runs/${runId}/client-requests`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setRequest(req);
      setMessage(req.body);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  async function markSent() {
    if (!request) return;
    await api(`/client-requests/${request.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "approved" }),
    });
    const sent = await api<ClientRequest>(`/client-requests/${request.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "sent" }),
    });
    setRequest(sent);
  }

  function download(path: string) {
    const token = localStorage.getItem("access_token");
    window.open(`${API_URL}${path}?token=${token}`, "_blank");
    // Prefer fetch blob for auth header
    fetch(`${API_URL}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = path.includes("pdf") ? "working-paper.pdf" : "working-paper.xlsx";
        a.click();
        URL.revokeObjectURL(url);
      });
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-ash-bright">Review findings</h1>
      {error && <p className="text-sm text-red-300">{error}</p>}
      <ul className="space-y-4">
        {findings.map((f) => (
          <li
            key={f.id}
            className="rounded-panel border border-line bg-void-elevated p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-semibold">{f.title}</p>
                <p className="text-sm text-ink-muted">
                  {f.category} · {f.severity} · {f.status}
                </p>
                <p className="mt-2 text-sm">{f.description}</p>
                <p className="mt-2 text-sm text-ink-muted">
                  {f.recommended_action}
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  className="rounded-pill border border-line px-3 py-1 text-xs"
                  onClick={() => setStatus(f.id, "accepted")}
                >
                  Accept
                </button>
                <button
                  type="button"
                  className="rounded-pill border border-line px-3 py-1 text-xs"
                  onClick={() => setStatus(f.id, "dismissed")}
                >
                  Dismiss
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={generateRequest}
          className="rounded-pill bg-cta px-4 py-2 text-sm font-medium text-cta-ink"
        >
          Generate client request
        </button>
        <button
          type="button"
          onClick={() => download(`/runs/${runId}/export.xlsx`)}
          className="rounded-pill border border-line px-4 py-2 text-sm"
        >
          Export Excel
        </button>
        <button
          type="button"
          onClick={() => download(`/runs/${runId}/export.pdf`)}
          className="rounded-pill border border-line px-4 py-2 text-sm"
        >
          Export PDF
        </button>
      </div>
      {message && (
        <div className="space-y-3 rounded-panel border border-line bg-void-elevated p-4">
          <textarea
            className="h-40 w-full rounded-xl border border-line bg-void px-3 py-2 text-sm"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded-pill border border-line px-3 py-1 text-xs"
              onClick={() => navigator.clipboard.writeText(message)}
            >
              Copy
            </button>
            {request && request.status !== "sent" && (
              <button
                type="button"
                className="rounded-pill border border-line px-3 py-1 text-xs"
                onClick={markSent}
              >
                Mark sent
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
