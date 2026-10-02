"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  return (
    <div className="min-h-screen">
      <header className="border-b border-line px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link href="/dashboard" className="font-semibold text-ash-bright">
            GST Workbench
          </Link>
          <nav className="flex items-center gap-4 text-sm text-ink-muted">
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/clients">Clients</Link>
            <button
              type="button"
              onClick={() => {
                clearToken();
                router.push("/login");
              }}
              className="text-ink-faint"
            >
              Sign out
            </button>
          </nav>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-6 py-8">{children}</div>
    </div>
  );
}
