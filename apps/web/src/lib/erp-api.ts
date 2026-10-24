const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

export type ErpDocument = {
  id: string;
  filename: string;
  kind: string;
  mime: string;
  size_bytes: number;
  uploaded_at: string;
  source: string;
  status: string;
  summary: string;
  row_count: number;
  tags: string[];
};

export type EnterpriseSummary = {
  title: string;
  subtitle: string;
  health_score: number;
  kpis: { id: string; label: string; value: string; hint: string }[];
  supply_chain: {
    tiers: number;
    nodes: number;
    links: number;
    monthly_goods_label: string;
    concentration: { top_vendor: string | null; top_share_pct: string; vendor_count: number };
    top_vendors: { name: string; amount_cents: number }[];
    top_customers: { name: string; amount_cents: number }[];
    dynamics: string[];
  };
  chart_of_accounts: {
    count: number;
    by_type: Record<string, number>;
    top_balances: { code: string; name: string; account_type: string; balance_cents: number }[];
  };
  documents: ErpDocument[];
  integrations: Record<string, { status: string; last_sync: string | null }>;
  sow: { runway_days: number; work_items: number; policies: number; open_holds: number };
  recommendations: string[];
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, { ...init, cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

export const erpApi = {
  snapshot: () => req<{ documents: ErpDocument[]; totals: Record<string, number>; integrations: EnterpriseSummary["integrations"]; accounts: unknown[]; parties: unknown[] }>("/v1/erp"),
  summary: () => req<EnterpriseSummary>("/v1/erp/summary"),
  seedSamples: () => req<{ documents: number }>("/v1/erp/seed-samples", { method: "POST" }),
  upload: async (file: File, kindHint?: string, scanText?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (kindHint) fd.append("kind_hint", kindHint);
    if (scanText) fd.append("scan_text", scanText);
    const res = await fetch(`${API}/v1/erp/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  scanText: async (text: string, filename = "scanned_financial.txt") => {
    const fd = new FormData();
    fd.append("text", text);
    fd.append("filename", filename);
    const res = await fetch(`${API}/v1/erp/scan-text`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  /** Index FinDoc OCR + FinCriticalED samples from data/train_data */
  trainBatch: (perClass = 3, fincriticalLimit = 3) =>
    req<{
      ocr_ingested: number;
      totals: Record<string, number>;
      fincritical?: { ingested?: number };
    }>(
      `/v1/erp/intake/train-batch?per_class=${perClass}&fincritical_limit=${fincriticalLimit}`,
      { method: "POST" },
    ),
  ingestOcr: async (file: File, hintedClass?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (hintedClass) fd.append("hinted_class", hintedClass);
    const res = await fetch(`${API}/v1/erp/intake/ocr`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  /** Bulk DocILE annotations → per-business customer / supply / relationship store */
  ingestDocile: (limit = 40) =>
    req<{
      ok: boolean;
      ingested: number;
      businesses_touched: number;
      business_index: BizSummary[];
      erp_totals: Record<string, number>;
      error?: string;
    }>(`/v1/erp/intake/docile?limit=${limit}`, { method: "POST" }),
  ingestDocileFile: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API}/v1/erp/intake/docile/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  businesses: () => req<{ businesses: BizSummary[]; count: number }>("/v1/erp/businesses"),
  business: (bizId: string) =>
    req<{ profile: BizProfile; graph: unknown }>(`/v1/erp/businesses/${encodeURIComponent(bizId)}`),
};

export type BizSummary = {
  id: string;
  name: string;
  tax_id: string;
  address: string;
  invoice_count: number;
  total_invoiced_cents: number;
  total_due_cents: number;
  customer_count: number;
  supplier_count: number;
  sku_count: number;
  document_types: Record<string, number>;
  updated_at: string;
};

export type BizProfile = BizSummary & {
  customers: Record<string, { name: string; invoice_count: number; amount_cents: number; billing_address?: string }>;
  suppliers: Record<string, { name: string; hits: number; amount_cents: number }>;
  relationships: { counterparty: string; role: string; strength: number; amount_cents: number }[];
  line_skus: Record<string, { description: string; hits: number; amount_cents: number }>;
  meta: Record<string, unknown>;
};