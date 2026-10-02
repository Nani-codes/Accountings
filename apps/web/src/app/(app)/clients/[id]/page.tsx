"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";

type Client = {
  id: string;
  name: string;
  gstin: string | null;
  gst_review_status: string | null;
};

export default function ClientWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [client, setClient] = useState<Client | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    api<Client>(`/clients/${id}`)
      .then(setClient)
      .catch((e) => setError(e.message));
  }, [id, router]);

  if (error) return <p className="text-red-300">{error}</p>;
  if (!client) return <p className="text-ink-muted">Loading…</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ash-bright">{client.name}</h1>
        <p className="text-ink-muted">
          Status: {client.gst_review_status || "No run yet"}
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          href={`/clients/${id}/upload`}
          className="rounded-pill bg-cta px-4 py-2 text-sm font-medium text-cta-ink"
        >
          Upload / start run
        </Link>
      </div>
      <p className="text-sm text-ink-faint">
        Document checklist and findings summary expand after the first run
        (upload flow).
      </p>
    </div>
  );
}
