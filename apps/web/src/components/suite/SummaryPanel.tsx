"use client";

import { useCallback, useEffect, useState } from "react";
import { erpApi, type EnterpriseSummary } from "@/lib/erp-api";
import { formatUsd } from "@swarmcfo/shared";

export function SummaryPanel() {
  const [data, setData] = useState<EnterpriseSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await erpApi.summary());
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "summary offline");
    }
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 8000);
    return () => clearInterval(t);
  }, [load]);

  if (err && !data) {
    return (
      <p className="err">
        Start `npm run agents` (port 8765). {err}
        <style jsx>{`
          .err {
            color: var(--warn);
            padding: 2rem;
          }
        `}</style>
      </p>
    );
  }
  if (!data) return <p className="loading">Loading enterprise summary…</p>;

  return (
    <section className="sum">
      <header>
        <div>
          <h1>{data.title}</h1>
          <p>{data.subtitle}</p>
        </div>
        <div className="health">
          <span>Enterprise health</span>
          <strong className="mono">{data.health_score}</strong>
        </div>
      </header>

      <div className="kpis">
        {data.kpis.map((k) => (
          <article key={k.id}>
            <span>{k.label}</span>
            <p className="mono">{k.value}</p>
            <small>{k.hint}</small>
          </article>
        ))}
      </div>

      <div className="grid">
        <article className="panel">
          <h2>Supply chain dynamics</h2>
          <p className="meta">
            {data.supply_chain.tiers} tiers · {data.supply_chain.nodes} nodes ·{" "}
            {data.supply_chain.links} links · {data.supply_chain.monthly_goods_label} goods flow
          </p>
          <ul className="dynamics">
            {data.supply_chain.dynamics.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
          <div className="two">
            <div>
              <h3>Top vendors</h3>
              <ul>
                {data.supply_chain.top_vendors.map((v) => (
                  <li key={v.name}>
                    <span>{v.name}</span>
                    <span className="mono">{formatUsd(v.amount_cents)}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Top customers</h3>
              <ul>
                {data.supply_chain.top_customers.map((c) => (
                  <li key={c.name}>
                    <span>{c.name}</span>
                    <span className="mono">{formatUsd(c.amount_cents)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <p className="conc">
            Concentration: {data.supply_chain.concentration.top_vendor ?? "—"} ·{" "}
            {data.supply_chain.concentration.top_share_pct} of AP
          </p>
        </article>

        <article className="panel">
          <h2>Chart of accounts</h2>
          <p className="meta">{data.chart_of_accounts.count} accounts indexed from vault</p>
          <div className="types">
            {Object.entries(data.chart_of_accounts.by_type).map(([t, n]) => (
              <span key={t}>
                {t} {n}
              </span>
            ))}
          </div>
          <ul className="acct">
            {data.chart_of_accounts.top_balances.map((a) => (
              <li key={a.code}>
                <span>
                  {a.code} · {a.name}
                </span>
                <span className="mono">{formatUsd(a.balance_cents)}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <h2>ERP integrations</h2>
          <ul className="integ">
            {Object.entries(data.integrations).map(([name, info]) => (
              <li key={name}>
                <strong>
                  {name}
                  {name === "nessie" ? " · Capital One" : ""}
                </strong>
                <span>
                  {info.status}
                  {name === "nessie" ? " · Powered by Nessie" : ""}
                </span>
              </li>
            ))}
          </ul>
          <h3>System of work</h3>
          <p className="meta">
            Runway {data.sow.runway_days}d · {data.sow.work_items} work items · {data.sow.policies}{" "}
            policies · {data.sow.open_holds} holds
          </p>
        </article>

        <article className="panel">
          <h2>Recommendations</h2>
          <ul className="recs">
            {data.recommendations.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </article>
      </div>

      <style jsx>{`
        .sum {
          padding: 1.5rem 2rem 3rem;
        }
        header {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-end;
          margin-bottom: 1.25rem;
        }
        h1 {
          font-family: var(--font-display);
          font-size: clamp(1.8rem, 4vw, 2.4rem);
          margin: 0;
        }
        header p {
          margin: 0.35rem 0 0;
          color: var(--ink-muted);
        }
        .health {
          text-align: right;
        }
        .health span {
          display: block;
          font-size: 0.72rem;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--ink-muted);
        }
        .health strong {
          font-family: var(--font-display);
          font-size: 3rem;
          color: var(--accent-bright);
          line-height: 1;
        }
        .kpis {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 0.65rem;
          margin-bottom: 1.25rem;
        }
        .kpis article {
          padding: 0.9rem 1rem;
          border: 1px solid var(--line);
          border-radius: 12px;
          background: rgba(26, 42, 34, 0.55);
        }
        .kpis span {
          font-size: 0.72rem;
          color: var(--ink-muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }
        .kpis p {
          margin: 0.35rem 0 0.15rem;
          font-size: 1.35rem;
          font-weight: 700;
        }
        .kpis small {
          color: var(--ink-muted);
          font-size: 0.75rem;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 0.85rem;
        }
        .panel {
          padding: 1.1rem 1.2rem;
          border: 1px solid var(--line);
          border-radius: 14px;
          background: rgba(12, 18, 16, 0.55);
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.15rem;
          margin: 0 0 0.35rem;
        }
        h3 {
          font-size: 0.85rem;
          margin: 0.85rem 0 0.4rem;
          color: var(--ink-muted);
        }
        .meta {
          margin: 0 0 0.75rem;
          color: var(--ink-muted);
          font-size: 0.85rem;
        }
        .dynamics,
        .recs {
          margin: 0;
          padding-left: 1.1rem;
          color: var(--ink-muted);
          font-size: 0.88rem;
          line-height: 1.45;
        }
        .two {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.75rem;
        }
        .two ul,
        .acct,
        .integ {
          list-style: none;
          margin: 0;
          padding: 0;
        }
        .two li,
        .acct li,
        .integ li {
          display: flex;
          justify-content: space-between;
          gap: 0.5rem;
          font-size: 0.82rem;
          padding: 0.3rem 0;
          border-bottom: 1px solid var(--line);
        }
        .conc {
          margin: 0.85rem 0 0;
          font-size: 0.8rem;
          color: var(--warn);
        }
        .types {
          display: flex;
          flex-wrap: wrap;
          gap: 0.35rem;
          margin-bottom: 0.65rem;
        }
        .types span {
          font-size: 0.7rem;
          padding: 0.2rem 0.45rem;
          border-radius: 4px;
          background: var(--bg-deep);
          color: var(--ink-muted);
        }
        .integ strong {
          text-transform: capitalize;
        }
        .integ span {
          color: var(--accent-bright);
          font-size: 0.75rem;
        }
        .loading {
          padding: 2rem;
          color: var(--ink-muted);
        }
      `}</style>
    </section>
  );
}