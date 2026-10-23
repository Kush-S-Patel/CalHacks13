/**
 * Client-side demo store until SpacetimeDB subscriptions are wired.
 * Mirrors the shared world so the UI / phone / big screen stay in sync in-process.
 */

import { DEMO_SEED, formatUsd, runwayDays, type ChaosKind } from "@swarmcfo/shared";

export type ActionRow = {
  id: string;
  agent: string;
  actionType: string;
  targetId: string;
  rationale: string;
  amountCents: number;
  at: number;
};

export type ApprovalRow = {
  id: string;
  description: string;
  amountCents: number;
  status: "waiting" | "approved" | "rejected";
};

export type WorldState = {
  cashBalanceCents: number;
  dailyBurnCents: number;
  runwayDays: number;
  actions: ActionRow[];
  approvals: ApprovalRow[];
  chaosInjected: ChaosKind[];
};

const listeners = new Set<() => void>();

let state: WorldState = {
  cashBalanceCents: DEMO_SEED.cashBalanceCents,
  dailyBurnCents: DEMO_SEED.dailyBurnCents,
  runwayDays: DEMO_SEED.runwayDays,
  actions: [],
  approvals: [],
  chaosInjected: [],
};

function emit() {
  listeners.forEach((l) => l());
}

function pushAction(
  agent: string,
  actionType: string,
  targetId: string,
  rationale: string,
  amountCents = 0,
) {
  state = {
    ...state,
    actions: [
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        agent,
        actionType,
        targetId,
        rationale,
        amountCents,
        at: Date.now(),
      },
      ...state.actions,
    ].slice(0, 40),
  };
}

export function getWorld(): WorldState {
  return state;
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export async function injectChaos(kind: ChaosKind): Promise<void> {
  if (state.chaosInjected.includes(kind)) return;

  state = { ...state, chaosInjected: [...state.chaosInjected, kind] };

  // Fan-out to agent service when available; always apply local deterministic effects.
  try {
    await fetch("http://127.0.0.1:8000/v1/demo/chaos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kinds: [kind] }),
    });
  } catch {
    // offline — local replay still works
  }

  if (kind === "duplicate_invoice") {
    pushAction(
      "risk",
      "block",
      "inv-dup-incoming",
      "Duplicate detected (amount + bank + date hash) — BLOCKED. Saved $4,200.",
      420_000,
    );
  }

  if (kind === "price_spike") {
    pushAction(
      "procurement",
      "counter",
      "sup-flour-co→sup-alt-flour",
      "Flour +40%. Counter-offer SENT to Coastal Grain Alt — ~$2,728/mo saved.",
      272_800,
    );
    pushAction(
      "risk",
      "flag",
      "sup-alt-flour",
      "Alt supplier trust_score 0.70 — distrust until trial.",
    );
    pushAction(
      "cfo",
      "arbitrate",
      "sup-alt-flour",
      "Decision: trial alt + watchlist. Procurement savings win; Risk stays on watch.",
    );
  }

  if (kind === "late_ar") {
    pushAction(
      "collections",
      "chase",
      "ar-big-cafe",
      "Harbor Cafe $9,200 / 12d late — firm chase + 2% early-pay incentive SENT.",
      920_000,
    );
  }

  // After any chaos, CFO may defer + cashier holds deposit once all three fired
  if (state.chaosInjected.length >= 3 && !state.approvals.some((a) => a.id === "appr-supplier-deposit")) {
    pushAction(
      "cfo",
      "defer",
      "noncritical-spend",
      "Defer $3,800 packaging refresh — runway extends.",
      380_000,
    );
    // Pitch: defer $3.8k + accelerated AR $9.2k + blocked dup $4.2k → ~20 days
    const cash = state.cashBalanceCents + 380_000 + 920_000 + 420_000;
    const days = runwayDays(cash, state.dailyBurnCents);
    state = {
      ...state,
      cashBalanceCents: cash,
      runwayDays: days,
    };
    pushAction(
      "cfo",
      "announce",
      "runway",
      `Runway ${DEMO_SEED.runwayDays.toFixed(0)} → ${days.toFixed(0)} days (defer + accelerated AR).`,
    );

    state = {
      ...state,
      approvals: [
        {
          id: "appr-supplier-deposit",
          description: "Supplier deposit — North Bay Flour Co",
          amountCents: 140_000,
          status: "waiting",
        },
        ...state.approvals,
      ],
    };
    pushAction(
      "cashier",
      "hold",
      "appr-supplier-deposit",
      `$1,400 exceeds $1,000 autonomy — WAITING for owner Approve.`,
      140_000,
    );
  }

  emit();
}

export function approve(approvalId: string): void {
  const approval = state.approvals.find((a) => a.id === approvalId);
  if (!approval || approval.status !== "waiting") return;

  const cash = state.cashBalanceCents - approval.amountCents;
  state = {
    ...state,
    cashBalanceCents: cash,
    runwayDays: runwayDays(cash, state.dailyBurnCents),
    approvals: state.approvals.map((a) =>
      a.id === approvalId ? { ...a, status: "approved" as const } : a,
    ),
  };
  pushAction(
    "owner",
    "approve",
    approvalId,
    `Owner approved ${formatUsd(approval.amountCents)} — every screen updates.`,
    approval.amountCents,
  );
  emit();
}

export function resetDemo(): void {
  state = {
    cashBalanceCents: DEMO_SEED.cashBalanceCents,
    dailyBurnCents: DEMO_SEED.dailyBurnCents,
    runwayDays: DEMO_SEED.runwayDays,
    actions: [],
    approvals: [],
    chaosInjected: [],
  };
  emit();
}