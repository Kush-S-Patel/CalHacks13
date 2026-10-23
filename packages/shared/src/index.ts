export const ROOM_ID = "maya-bakery";

export const AGENTS = ["cfo", "risk", "procurement", "collections", "cashier"] as const;
export type AgentName = (typeof AGENTS)[number];

export const AGENT_LABELS: Record<AgentName, string> = {
  cfo: "CFO",
  risk: "Risk / Fraud",
  procurement: "Procurement",
  collections: "Collections",
  cashier: "Cashier",
};

export const CASHIER_AUTO_PAY_LIMIT_CENTS = 100_000; // $1,000

export const DEMO_SEED = {
  ownerName: "Maya",
  businessName: "Maya's Bakery",
  cashBalanceCents: 1_840_000, // $18,400
  dailyBurnCents: 165_000, // $1,650
  runwayDays: 18400 / 1650, // ~11.15
} as const;

export type ChaosKind = "price_spike" | "duplicate_invoice" | "late_ar";

export const CHAOS_BUTTONS: { kind: ChaosKind; label: string; detail: string }[] = [
  {
    kind: "price_spike",
    label: "Price spike +40%",
    detail: "Flour supplier raises prices",
  },
  {
    kind: "duplicate_invoice",
    label: "Duplicate $4,200",
    detail: "Same amount + bank + date",
  },
  {
    kind: "late_ar",
    label: "Late AR $9,200",
    detail: "Harbor Cafe — 12 days late",
  },
];

export function formatUsd(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

export function runwayDays(cashCents: number, burnCents: number): number {
  if (burnCents <= 0) return 999;
  return cashCents / burnCents;
}