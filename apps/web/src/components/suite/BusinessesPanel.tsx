"use client";

import { useCallback, useEffect, useState } from "react";
import { erpApi, type BizProfile, type BizSummary } from "@/lib/erp-api";
import { formatUsd } from "@swarmcfo/shared";

export function BusinessesPanel() {
  const [list, setList] = useState<BizSummary[]>([]);
  const [selected, setSelected] = useState<BizProfile | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await erpApi.businesses();
      setList(res.businesses);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "businesses offline");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function openBiz(id: string) {
    try {
      const res = await erpApi.business(id);
      setSelected(res.profile);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "load failed");
    }
  }

  async function ingestDocile() {
    setBusy(true);
    setErr(null);
    try {
      const res = await erpApi.ingestDocile(60);
      if (!res.ok) throw new Error(res.error || "docile ingest failed");
      setList(res.business_index || []);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "docile ingest failed");
    } finally {
      setBusy(false);
    }
  }

  const customers = selected ? Object.values(selected.customers || {}) : [];
  const suppliers = selected ? Object.values(selected.suppliers || {}) : [];
  const skus = selected ? Object.values(selected.line_skus || {}).slice(0, 12) : [];

  return (
    <section className="biz">
      <header>
        <div>
          <h1>Enterprises</h1>
          <p>
            Per-business knowledge from DocILE invoices — customers, supply-chain parties,
            SKUs, and relationship strength stored under each issuing vendor.
          </p>
        </div>
        <button type="button" disabled={busy} onClick={() => void ingestDocile()}>
          {busy ? "Indexing DocILE…" : "Ingest DocILE (60 docs)"}
        </button>
      </header>

      {err && <p className="err">{err}</p>}

      <div className="layout">
        <ul className="list">
          {list.length === 0 && (
            <li className="empty">No businesses yet — ingest DocILE annotations from train_data.</li>
          )}
          {list.map((b) => (
            <li key={b.id}>
              <button
                type="button"
                className={selected?.id === b.id ? "on" : ""}
                onClick={() => void openBiz(b.id)}
              >
                <strong>{b.name}</strong>
                <span>
                  {b.invoice_count} inv · {b.customer_count} customers ·{" "}
                  {formatUsd(b.total_due_cents)}
                </span>
              </button>
            </li>
          ))}
        </ul>

        <div className="detail">
          {!selected && <p className="empty">Select a business to expand customer base &amp; supply links.</p>}
          {selected && (
            <>
              <h2>{selected.name}</h2>
              <p className="meta">
                {selected.tax_id && <>Tax ID {selected.tax_id} · </>}
                {selected.invoice_count} invoices · due {formatUsd(selected.total_due_cents)}
              </p>
              {selected.address && <p className="addr">{selected.address}</p>}

              <div className="cols">
                <div>
                  <h3>Customers ({customers.length})</h3>
                  <ul>
                    {customers
                      .sort((a, b) => b.amount_cents - a.amount_cents)
                      .slice(0, 20)
                      .map((c) => (
                        <li key={c.name}>
                          <strong>{c.name}</strong>
                          <span>
                            {c.invoice_count} docs · {formatUsd(c.amount_cents)}
                          </span>
                        </li>
                      ))}
                  </ul>
                </div>
                <div>
                  <h3>Supply / related ({suppliers.length})</h3>
                  <ul>
                    {suppliers
                      .sort((a, b) => b.amount_cents - a.amount_cents)
                      .slice(0, 20)
                      .map((s) => (
                        <li key={s.name}>
                          <strong>{s.name}</strong>
                          <span>
                            {s.hits} hits · {formatUsd(s.amount_cents)}
                          </span>
                        </li>
                      ))}
                    {suppliers.length === 0 && <li className="empty">No line-item parties yet</li>}
                  </ul>
                </div>
              </div>

              <h3>Relationships</h3>
              <ul className="rels">
                {(selected.relationships || [])
                  .sort((a, b) => b.strength - a.strength)
                  .slice(0, 25)
                  .map((r) => (
                    <li key={`${r.role}-${r.counterparty}`}>
                      <em>{r.role}</em> {r.counterparty}
                      <span>
                        ×{r.strength} · {formatUsd(r.amount_cents)}
                      </span>
                    </li>
                  ))}
              </ul>

              {skus.length > 0 && (
                <>
                  <h3>Line catalog</h3>
                  <ul className="skus">
                    {skus.map((s) => (
                      <li key={s.description}>
                        {s.description}
                        <span>
                          ×{s.hits} · {formatUsd(s.amount_cents)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          )}
        </div>
      </div>

      <style jsx>{`
        .biz {
          padding: 1.5rem 2rem 3rem;
          max-width: 1200px;
        }
        header {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-start;
          margin-bottom: 1.25rem;
        }
        h1 {
          font-family: var(--font-display);
          font-size: 1.75rem;
          margin: 0 0 0.35rem;
        }
        header p {
          color: var(--ink-muted);
          max-width: 36rem;
          margin: 0;
          font-size: 0.92rem;
        }
        header button {
          background: var(--accent, #2f6b4f);
          color: #e8f2ec;
          border: 0;
          border-radius: 8px;
          padding: 0.65rem 1rem;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
        }
        header button:disabled {
          opacity: 0.6;
        }
        .err {
          color: var(--warn);
          margin-bottom: 1rem;
        }
        .layout {
          display: grid;
          grid-template-columns: minmax(220px, 320px) 1fr;
          gap: 1.25rem;
        }
        @media (max-width: 800px) {
          .layout {
            grid-template-columns: 1fr;
          }
        }
        .list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
          max-height: 70vh;
          overflow: auto;
        }
        .list button {
          width: 100%;
          text-align: left;
          background: transparent;
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 0.75rem 0.9rem;
          color: var(--ink);
          cursor: pointer;
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }
        .list button.on,
        .list button:hover {
          background: #1a2a22;
          border-color: #3d5c4a;
        }
        .list button span,
        .detail .meta,
        .detail li span,
        .addr {
          color: var(--ink-muted);
          font-size: 0.8rem;
        }
        .detail {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 1.25rem 1.4rem;
          background: rgba(12, 18, 16, 0.4);
        }
        .detail h2 {
          margin: 0 0 0.35rem;
          font-family: var(--font-display);
        }
        .cols {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
          margin: 1rem 0;
        }
        @media (max-width: 700px) {
          .cols {
            grid-template-columns: 1fr;
          }
        }
        .detail ul {
          list-style: none;
          margin: 0;
          padding: 0;
        }
        .detail li {
          display: flex;
          justify-content: space-between;
          gap: 0.75rem;
          padding: 0.4rem 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.04);
          font-size: 0.88rem;
        }
        .rels em {
          color: #7eb892;
          font-style: normal;
          margin-right: 0.35rem;
          font-size: 0.75rem;
          text-transform: uppercase;
        }
        .empty {
          color: var(--ink-muted);
          font-size: 0.9rem;
        }
        h3 {
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--ink-muted);
          margin: 1rem 0 0.4rem;
        }
      `}</style>
    </section>
  );
}
