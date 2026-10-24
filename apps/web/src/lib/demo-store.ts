/**
 * Client store synced from the System of Work API.
 * SpacetimeDB subscriptions replace polling when wired.
 */

import { DEMO_SEED } from "@swarmcfo/shared";
import { api, type AuditEvent, type Score, type WorkItem, type WorldSnapshot } from "./api";

export type ActionRow = {
  id: string;
  agent: string;
  actionType: string;
  targetId: string;
  rationale: string;
  amountCents: number;
  at: number;
  allowed?: boolean;
  diff?: Record<string, unknown>;
};

export type WorldState = {
  cashBalanceCents: number;
  dailyBurnCents: number;
  runwayDays: number;
  actions: ActionRow[];
  workItems: WorkItem[];
  policies: WorldSnapshot["policies"];
  holds: WorkItem[];
  needsInfo: WorkItem[];
  score: Score | null;
  audit: AuditEvent[];
  ready: boolean;
  error: string | null;
};

const listeners = new Set<() => void>();

let state: WorldState = {
  cashBalanceCents: DEMO_SEED.cashBalanceCents,
  dailyBurnCents: DEMO_SEED.dailyBurnCents,
  runwayDays: DEMO_SEED.runwayDays,
  actions: [],
  workItems: [],
  policies: [],
  holds: [],
  needsInfo: [],
  score: null,
  audit: [],
  ready: false,
  error: null,
};

function emit() {
  listeners.forEach((l) => l());
}

function applySnapshot(snap: WorldSnapshot, audit?: AuditEvent[]) {
  const events = audit ?? state.audit;
  state = {
    cashBalanceCents: snap.cash_balance_cents,
    dailyBurnCents: snap.daily_burn_cents,
    runwayDays: snap.runway_days,
    workItems: snap.work_items ?? [],
    policies: snap.policies ?? [],
    holds: snap.open_holds ?? [],
    needsInfo: snap.needs_info ?? [],
    score: snap.score ?? state.score,
    audit: events,
    ready: true,
    error: null,
    actions: events
      .slice()
      .reverse()
      .slice(0, 40)
      .map((e) => ({
        id: e.id,
        agent: e.actor,
        actionType: e.action,
        targetId: e.subject,
        rationale: e.reason,
        amountCents: 0,
        at: Date.parse(e.at) || Date.now(),
        allowed: e.allowed,
        diff: e.diff && Object.keys(e.diff).length ? e.diff : undefined,
      })),
  };
  emit();
}

export function getWorld(): WorldState {
  return state;
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function friendlyError(raw: string): string {
  if (raw.includes("Not Found") || raw.includes('"detail"')) {
    return "API not found on this port — run `npm run agents` (port 8765), not whatever is on 8000.";
  }
  return raw.slice(0, 160);
}

export async function refresh(): Promise<void> {
  try {
    const [snap, audit] = await Promise.all([api.world(), api.audit()]);
    applySnapshot(snap, audit.events);
  } catch (e) {
    const msg = e instanceof Error ? friendlyError(e.message) : "API offline";
    state = { ...state, error: msg, ready: false };
    emit();
  }
}

export async function runFullDemo(): Promise<void> {
  await api.runDemo();
  await refresh();
}

export async function approve(workItemId: string): Promise<void> {
  await api.approve(workItemId);
  await refresh();
}

export async function reject(workItemId: string, reason: string): Promise<void> {
  await api.reject(workItemId, reason);
  await refresh();
}

export async function answer(workItemId: string, text: string): Promise<void> {
  await api.answer(workItemId, text);
  await refresh();
}

export async function resetDemo(): Promise<void> {
  await api.reset();
  await refresh();
}

/** Chaos buttons map to running the answer-key demo (or refresh if already run). */
export async function injectChaos(_kind?: string): Promise<void> {
  await runFullDemo();
}