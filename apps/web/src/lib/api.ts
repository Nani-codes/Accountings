const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type TokenResponse = { access_token: string; token_type: string };

function authHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
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

export function storeToken(token: string) {
  localStorage.setItem("access_token", token);
}

export function clearToken() {
  localStorage.removeItem("access_token");
}
