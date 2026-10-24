export type GraphNode = {
  id: string;
  label: string;
  kind: string;
  amount_cents?: number;
  amount_label?: string;
  fraud?: boolean;
  held?: boolean;
  tier?: number;
  tier_label?: string;
  meta?: Record<string, unknown>;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  amount_cents: number;
  amount_label: string;
  label: string;
  kind: string;
  fraud?: boolean;
  held?: boolean;
  policy_id?: string;
  work_item_id?: string;
};

export type GraphPayload = {
  id: string;
  title: string;
  subtitle: string;
  layout: "hierarchical" | "force";
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type GraphsResponse = {
  supply_chain: GraphPayload;
  context: GraphPayload;
  relationships: GraphPayload;
  legend: Record<string, string>;
  stats: Record<string, number | string>;
};