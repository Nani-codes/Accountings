"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type Client = {
  id: string;
  name: string;
  gstin: string | null;
  services: string[];
  gst_review_status: string | null;
};

export default function ClientsPage() {
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [name, setName] = useState("");
  const [gstin, setGstin] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const rows = await api<Client[]>("/clients");
    setClients(rows);
  }

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    load().catch((e) => setError(e.message));
  }, [router]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/clients", {
        method: "POST",
        body: JSON.stringify({ name, gstin: gstin || null }),
      });
      setName("");
      setGstin("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-ash-bright">Clients</h1>
      <form onSubmit={onCreate} className="flex flex-wrap gap-2">
        <input
          className="rounded-xl border border-line bg-void-elevated px-3 py-2"
          placeholder="Client name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          className="rounded-xl border border-line bg-void-elevated px-3 py-2"
          placeholder="GSTIN (optional)"
          value={gstin}
          onChange={(e) => setGstin(e.target.value)}
        />
        <button
          type="submit"
          className="h-10 rounded-pill bg-cta px-4 text-sm font-medium text-cta-ink"
        >
          Add client
        </button>
      </form>
      {error && <p className="text-sm text-red-300">{error}</p>}
      <ul className="space-y-3">
        {clients.map((c) => (
          <li key={c.id} className="border-b border-line py-3">
            <Link
              href={`/clients/${c.id}`}
              className="text-lg font-medium text-ash-bright hover:underline"
            >
              {c.name}
            </Link>
            <p className="text-sm text-ink-muted">
              {(c.services || []).join(" | ")}
              {c.gst_review_status ? ` · GST Review: ${c.gst_review_status}` : ""}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
