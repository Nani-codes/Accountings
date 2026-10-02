"use client";

import { FormEvent, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const SLOTS = [
  { key: "purchase_register", label: "Purchase Register", required: true },
  { key: "gstr2b", label: "GSTR-2B", required: true },
  { key: "sales_register", label: "Sales Register", required: false },
  {
    key: "previous_reconciliation",
    label: "Previous reconciliation",
    required: false,
  },
  { key: "bank_statement", label: "Bank Statement", required: false },
] as const;

export default function UploadPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [period, setPeriod] = useState("2026-03");
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }
    try {
      setStatus("Creating run…");
      const runRes = await fetch(`${API_URL}/clients/${id}/runs`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ period }),
      });
      if (!runRes.ok) throw new Error(await runRes.text());
      const run = await runRes.json();

      for (const slot of SLOTS) {
        const file = files[slot.key];
        if (!file) {
          if (slot.required) throw new Error(`${slot.label} is required`);
          continue;
        }
        setStatus(`Uploading ${slot.label}…`);
        const body = new FormData();
        body.append("doc_type", slot.key);
        body.append("file", file);
        const up = await fetch(`${API_URL}/runs/${run.id}/documents`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body,
        });
        if (!up.ok) throw new Error(await up.text());
      }

      setStatus("Reconciling…");
      const start = await fetch(`${API_URL}/runs/${run.id}/start`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!start.ok) throw new Error(await start.text());
      const started = await start.json();
      router.push(`/clients/${id}/runs/${started.id}/review`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus(null);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-ash-bright">Upload files</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <label className="block text-sm text-ink-muted">
          Period (YYYY-MM)
          <input
            className="mt-1 block w-40 rounded-xl border border-line bg-void-elevated px-3 py-2 text-ink"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            pattern="\d{4}-\d{2}"
            required
          />
        </label>
        {SLOTS.map((slot) => (
          <label key={slot.key} className="block text-sm">
            <span className="text-ink-muted">
              {slot.label}
              {slot.required ? " *" : ""}
            </span>
            <input
              className="mt-1 block w-full text-sm"
              type="file"
              accept=".csv,.xlsx,.xls,.json"
              onChange={(e) =>
                setFiles((prev) => ({
                  ...prev,
                  [slot.key]: e.target.files?.[0] || null,
                }))
              }
              required={slot.required}
            />
          </label>
        ))}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {status && <p className="text-sm text-ink-muted">{status}</p>}
        <button
          type="submit"
          className="rounded-pill bg-cta px-4 py-2 text-sm font-medium text-cta-ink"
        >
          Upload & reconcile
        </button>
      </form>
    </div>
  );
}
