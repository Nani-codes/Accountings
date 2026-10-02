"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login, signup, storeToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token =
        mode === "login"
          ? await login({ email, password })
          : await signup({
              email,
              password,
              name,
              firm_name: firmName,
            });
      storeToken(token.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auth failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6">
      <div>
        <p className="text-sm text-ink-muted">GST Workbench</p>
        <h1 className="mt-2 text-2xl font-bold text-ash-bright">
          {mode === "login" ? "Sign in" : "Create firm account"}
        </h1>
      </div>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        {mode === "signup" && (
          <>
            <input
              className="rounded-xl border border-line bg-void-elevated px-3 py-2"
              placeholder="Your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <input
              className="rounded-xl border border-line bg-void-elevated px-3 py-2"
              placeholder="Firm name"
              value={firmName}
              onChange={(e) => setFirmName(e.target.value)}
              required
            />
          </>
        )}
        <input
          className="rounded-xl border border-line bg-void-elevated px-3 py-2"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="rounded-xl border border-line bg-void-elevated px-3 py-2"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
        {error && <p className="text-sm text-red-300">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="h-10 rounded-pill bg-cta text-sm font-medium text-cta-ink disabled:opacity-60"
        >
          {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Sign up"}
        </button>
      </form>
      <button
        type="button"
        className="text-sm text-ink-muted underline"
        onClick={() => setMode(mode === "login" ? "signup" : "login")}
      >
        {mode === "login"
          ? "Need an account? Sign up"
          : "Have an account? Sign in"}
      </button>
      <p className="text-xs text-ink-faint">
        Google OAuth appears when GOOGLE_CLIENT_ID is configured on the API.
      </p>
    </main>
  );
}
