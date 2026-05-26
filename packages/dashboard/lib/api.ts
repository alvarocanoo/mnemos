import "server-only";

const API_BASE = process.env.INTERNAL_API_URL ?? "http://service:8000";

export type Memory = {
  id: string;
  user_id: string;
  content: string;
  importance: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  access_count: number;
  last_accessed_at: string | null;
};

export type ScoreItem = {
  memory_id: string;
  importance: number;
  age_days: number;
  access_count: number;
  recency_weight: number;
  score: number;
};

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, { cache: "no-store", ...init });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GET ${url} failed (${res.status}): ${body.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${url} failed (${res.status}): ${text.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export async function listMemories(
  userId = "default",
  limit = 100,
): Promise<Memory[]> {
  return getJSON<Memory[]>(`/memories?user_id=${encodeURIComponent(userId)}&limit=${limit}`);
}

export async function readyz(): Promise<unknown> {
  return getJSON<unknown>("/readyz");
}

export async function scoreEviction(userId = "default"): Promise<ScoreItem[]> {
  return postJSON<ScoreItem[]>(
    `/memories/score-eviction?user_id=${encodeURIComponent(userId)}`,
    {},
  );
}

export function apiBase(): string {
  return API_BASE;
}
