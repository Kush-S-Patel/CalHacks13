const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

export type WorkItem = {
  id: string;
  kind: string;
  state: string;
  subject: string;
  title: string;
  amount_cents: number;
  proposed_by?: string | null;
  policy_id?: string | null;
  question?: string | null;
  answer?: string | null;
  payload?: Record<string, unknown>;
  evidence?: string[];
};

export type Policy = {
  id: string;
  version: number;
  title: string;
  rule: string;
  status: string;
  evidence: string[];
};

export type AuditEvent = {
  id: string;
  at: string;
  actor: string;
  action: string;
  subject: string;
  allowed: boolean;
  reason: string;
  diff: Record<string, unknown>;
};

export type Score = {
  hyphenate_score: number;
  checks: Record<string, boolean>;
  wow: Record<string, number>;
  judging: Record<string, boolean>;
};

export type WorldSnapshot = {
  room_id: string;
  cash_balance_cents: number;
  daily_burn_cents: number;
  runway_days: number;
  work_items: WorkItem[];
  policies: Policy[];
  precedents: { id: string; summary: string; tags: string[] }[];
  open_holds: WorkItem[];
  needs_info: WorkItem[];
  gateway_posted: unknown[];
  audit_len: number;
  score?: Score;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  world: () => req<WorldSnapshot>("/v1/world"),
  graphs: () => req<import("./graph-types").GraphsResponse>("/v1/graphs"),
  audit: (subject?: string) =>
    req<{ events: AuditEvent[]; denials?: AuditEvent[] }>(
      subject ? `/v1/audit/${encodeURIComponent(subject)}` : "/v1/audit",
    ),
  score: () => req<Score>("/v1/score"),
  runDemo: () =>
    req<{
      score: Score;
      log: string[];
      nessie?: { ok?: boolean; used_nessie?: boolean; account_id?: string };
      nessie_marker?: string | null;
    }>("/v1/demo/run", { method: "POST" }),
  nessie: () => req<Record<string, unknown>>("/v1/nessie"),
  approve: (id: string) =>
    req<{ item: WorkItem; world: WorldSnapshot }>(`/v1/work/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ actor_id: "human-maya", reason: "one-tap Approve" }),
    }),
  reject: (id: string, reason: string) =>
    req(`/v1/work/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ actor_id: "human-maya", reason }),
    }),
  answer: (id: string, answer: string) =>
    req(`/v1/work/${id}/answer`, {
      method: "POST",
      body: JSON.stringify({ actor_id: "human-maya", answer }),
    }),
  reset: () => req<WorldSnapshot>("/v1/reset", { method: "POST" }),
};