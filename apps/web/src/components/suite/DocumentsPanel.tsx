"use client";

import { useCallback, useEffect, useState } from "react";
import { erpApi, type ErpDocument } from "@/lib/erp-api";

export function DocumentsPanel() {
  const [docs, setDocs] = useState<ErpDocument[]>([]);
  const [totals, setTotals] = useState<Record<string, number>>({});
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const snap = await erpApi.snapshot();
      setDocs(snap.documents);
      setTotals(snap.totals);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "vault offline");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="docs">
      <header>
        <h1>Document vault</h1>
        <p>
          Digital store for workbooks and scanned financials — adjacent to NetSuite / QuickBooks /
          bank feeds. {totals.documents ?? 0} files · {totals.accounts ?? 0} GL accounts ·{" "}
          {totals.parties ?? 0} parties.
        </p>
      </header>
      {err && <p className="err">{err}</p>}
      <ul>
        {docs.length === 0 && <li className="empty">No documents yet — upload or load samples.</li>}
        {docs.map((d) => (
          <li key={d.id}>
            <div>
              <strong>{d.filename}</strong>
              <p>
                {d.kind} · {d.status} · {d.row_count} rows · {d.source}
              </p>
              <p className="sum">{d.summary}</p>
            </div>
            <div className="meta mono">
              <span>{(d.size_bytes / 1024).toFixed(1)} KB</span>
              <span>{new Date(d.uploaded_at).toLocaleString()}</span>
            </div>
          </li>
        ))}
      </ul>
      <style jsx>{`
        .docs {
          padding: 1.5rem 2rem 3rem;
        }
        h1 {
          font-family: var(--font-display);
          margin: 0 0 0.35rem;
          font-size: 2rem;
        }
        header p {
          margin: 0 0 1.2rem;
          color: var(--ink-muted);
          max-width: 40rem;
        }
        ul {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 0.55rem;
        }
        li {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          padding: 0.95rem 1.1rem;
          border: 1px solid var(--line);
          border-radius: 12px;
          background: rgba(26, 42, 34, 0.45);
        }
        .empty {
          color: var(--ink-muted);
          border-style: dashed;
        }
        p {
          margin: 0.2rem 0 0;
          font-size: 0.82rem;
          color: var(--ink-muted);
        }
        .sum {
          color: var(--ink) !important;
        }
        .meta {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.25rem;
          font-size: 0.75rem;
          color: var(--ink-muted);
          white-space: nowrap;
        }
        .err {
          color: var(--danger);
        }
      `}</style>
    </section>
  );
}