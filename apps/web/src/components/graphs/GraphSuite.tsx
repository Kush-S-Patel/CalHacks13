"use client";

import { useCallback, useEffect, useState } from "react";
import type { GraphsResponse } from "@/lib/graph-types";
import { GraphCanvas } from "./GraphCanvas";

type Tab = "supply_chain" | "context" | "relationships";

const TABS: { id: Tab; label: string }[] = [
  { id: "supply_chain", label: "Supply chain" },
  { id: "context", label: "Context graph" },
  { id: "relationships", label: "Relationships" },
];

/** Prefer same-origin Next proxy, then agent, then static seed. */
const GRAPH_URLS = [
  "/api/graphs",
  `${process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765"}/graphs`,
  "/graphs.json",
];

export function GraphSuite({ compact = false }: { compact?: boolean }) {
  const [data, setData] = useState<GraphsResponse | null>(null);
  const [tab, setTab] = useState<Tab>("supply_chain");
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    let lastErr: unknown;
    for (const url of GRAPH_URLS) {
      try {
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) {
          lastErr = new Error(await res.text());
          continue;
        }
        const json = (await res.json()) as GraphsResponse;
        if (!json?.supply_chain?.nodes) {
          lastErr = new Error("invalid graph payload");
          continue;
        }
        setData(json);
        setErr(url === "/graphs.json" ? "Showing seed graphs (agent offline)." : null);
        return;
      } catch (e) {
        lastErr = e;
      }
    }
    setErr(lastErr instanceof Error ? lastErr.message : "graphs offline");
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 5000);
    return () => clearInterval(t);
  }, [load]);

  const graph = data?.[tab];

  return (
    <section className={`suite ${compact ? "compact" : ""}`}>
      <div className="head">
        <div>
          <h2>Company graph</h2>
          <p>
            Full supply chain, money context, and entity relationships — exact dollars, fraud
            marked in red.
          </p>
        </div>
        {data && (
          <div className="stats mono">
            <span>{data.stats.supply_tiers} tiers</span>
            <span>{data.stats.fraud_flags} fraud flags</span>
            <span>{data.stats.cash_balance_usd}</span>
          </div>
        )}
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={tab === t.id ? "on" : ""}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
        <button type="button" className="refresh" onClick={() => void load()}>
          Refresh
        </button>
      </div>

      {err && !data && (
        <p className="err">
          Start the agent API to load live graphs (`npm run agents`). {err}
        </p>
      )}

      {graph && <GraphCanvas graph={graph} height={compact ? 360 : 460} />}

      {data && (
        <ul className="legend">
          {Object.entries(data.legend).map(([k, v]) => (
            <li key={k}>
              <strong>{k}</strong> — {v}
            </li>
          ))}
        </ul>
      )}

      <style jsx>{`
        .suite {
          padding: 0 2rem 2rem;
        }
        .suite.compact {
          padding-top: 0.5rem;
        }
        .head {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-end;
          margin-bottom: 0.85rem;
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.45rem;
          margin: 0 0 0.25rem;
        }
        .head p {
          margin: 0;
          color: var(--ink-muted);
          font-size: 0.9rem;
          max-width: 36rem;
        }
        .stats {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
        }
        .stats span {
          font-size: 0.75rem;
          padding: 0.35rem 0.55rem;
          border: 1px solid var(--line);
          border-radius: 6px;
          color: var(--ink-muted);
        }
        .tabs {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
          margin-bottom: 0.75rem;
        }
        .tabs button {
          background: var(--bg-panel);
          border: 1px solid var(--line);
          color: var(--ink-muted);
          padding: 0.45rem 0.85rem;
          border-radius: 8px;
          font-size: 0.82rem;
          font-weight: 600;
        }
        .tabs button.on {
          color: var(--ink);
          border-color: var(--accent);
          background: #1f3328;
        }
        .tabs .refresh {
          margin-left: auto;
          font-weight: 500;
        }
        .err {
          color: var(--warn);
          font-size: 0.88rem;
        }
        .legend {
          list-style: none;
          margin: 0.85rem 0 0;
          padding: 0;
          display: flex;
          flex-wrap: wrap;
          gap: 0.65rem 1.25rem;
        }
        .legend li {
          font-size: 0.75rem;
          color: var(--ink-muted);
        }
        .legend strong {
          color: var(--ink);
          text-transform: capitalize;
        }
      `}</style>
    </section>
  );
}