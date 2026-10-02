"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type Dashboard = {
  clients: number;
  active_gst_reviews: number;
  exceptions: number;
  client_responses_pending: number;
  recent_activity: {
    client_id: string;
    client_name: string;
    label: string;
    run_id: string | null;
  }[];
};

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    api<Dashboard>("/dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, [router]);

  if (error) return <p className="text-red-300">{error}</p>;
  if (!data) return <p className="text-ink-muted">Loading…</p>;

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-ash-bright">{greeting}</h1>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          ["Clients", data.clients],
          ["Active GST reviews", data.active_gst_reviews],
          ["Exceptions", data.exceptions],
          ["Client responses pending", data.client_responses_pending],
        ].map(([label, value]) => (
          <div
            key={String(label)}
            className="rounded-panel border border-line bg-void-elevated p-4"
          >
            <p className="text-sm text-ink-muted">{label}</p>
            <p className="mt-2 text-2xl font-semibold">{value}</p>
          </div>
        ))}
      </div>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent activity</h2>
        <ul className="space-y-2">
          {data.recent_activity.length === 0 && (
            <li className="text-ink-muted">No runs yet.</li>
          )}
          {data.recent_activity.map((item) => (
            <li
              key={`${item.client_id}-${item.run_id}`}
              className="border-b border-line py-2"
            >
              <p className="font-medium">{item.client_name}</p>
              <p className="text-sm text-ink-muted">{item.label}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
