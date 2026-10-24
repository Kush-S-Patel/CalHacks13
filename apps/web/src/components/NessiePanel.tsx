"use client";

import { useCallback, useEffect, useState } from "react";
import { NessieBadge } from "./NessieBadge";

const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

type Tx = {
  at?: string;
  kind?: string;
  amount?: number;
  description?: string;
  nessie_id?: string;
  ok?: boolean;
};

type Snap = {
  status?: string;
  used_nessie?: boolean;
  marker?: string;
  account_id?: string;
  customer_id?: string;
  account_number_last4?: string;
  tx_count?: number;
  transactions?: Tx[];
  atms_nearby?: { name?: string }[];
};

export function NessiePanel() {
  const [data, setData] = useState<Snap | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/v1/nessie`, { cache: "no-store" });
      if (!res.ok) throw new Error(await res.text());
      setData(await res.json());
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "nessie offline");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function provision() {
    setBusy(true);
    try {
      await fetch(`${API}/v1/nessie/provision`, { method: "POST" });
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "provision failed");
    } finally {
      setBusy(false);
    }
  }

  async function syncDemo() {
    setBusy(true);
    try {
      await fetch(`${API}/v1/nessie/sync-demo`, { method: "POST" });
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "sync failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="np">
      <div className="head">
        <div>
          <h2>Capital One Nessie</h2>
          <p>Live bank-sim rail for Maya&apos;s operating account — deposits, withdrawals, nearby ATMs.</p>
        </div>
        <NessieBadge />
      </div>
      {err && <p className="err">{err}</p>}
      <div className="actions">
        <button type="button" disabled={busy} onClick={() => void provision()}>
          Provision Maya account
        </button>
        <button type="button" disabled={busy} onClick={() => void syncDemo()}>
          Sync demo cash events
        </button>
      </div>
      {data && (
        <div className="grid">
          <div>
            <span className="k">Status</span>
            <p>{data.status || "—"} · {data.marker}</p>
          </div>
          <div>
            <span className="k">Account</span>
            <p className="mono">****{data.account_number_last4 || "····"}</p>
          </div>
          <div>
            <span className="k">Nessie txs</span>
            <p className="mono">{data.tx_count ?? 0}</p>
          </div>
        </div>
      )}
      {data?.transactions && data.transactions.length > 0 && (
        <ul className="txs">
          {data.transactions.map((t, i) => (
            <li key={t.nessie_id || i}>
              <strong>{t.kind}</strong>
              <span>${Number(t.amount || 0).toLocaleString()}</span>
              <em>{t.description}</em>
            </li>
          ))}
        </ul>
      )}
      {data?.atms_nearby && data.atms_nearby.length > 0 && (
        <p className="atms">
          Nearby ATMs: {data.atms_nearby.map((a) => a.name).filter(Boolean).join(" · ")}
        </p>
      )}
      <style jsx>{`
        .np {
          margin: 0 2rem 1.5rem;
          padding: 1.1rem 1.25rem;
          border: 1px solid rgba(0, 114, 206, 0.35);
          border-radius: 12px;
          background: linear-gradient(135deg, rgba(0, 73, 119, 0.22), rgba(12, 18, 16, 0.5));
        }
        .head {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-start;
          flex-wrap: wrap;
        }
        h2 {
          margin: 0 0 0.25rem;
          font-family: var(--font-display);
          font-size: 1.15rem;
        }
        .head p {
          margin: 0;
          color: var(--ink-muted);
          font-size: 0.85rem;
          max-width: 28rem;
        }
        .actions {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin: 0.9rem 0;
        }
        button {
          background: #004977;
          color: #e8f4ff;
          border: 0;
          border-radius: 8px;
          padding: 0.5rem 0.85rem;
          font-weight: 600;
          font-size: 0.8rem;
          cursor: pointer;
        }
        button:disabled {
          opacity: 0.55;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.75rem;
          margin-bottom: 0.75rem;
        }
        @media (max-width: 700px) {
          .grid {
            grid-template-columns: 1fr;
          }
        }
        .k {
          display: block;
          font-size: 0.65rem;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--ink-muted);
        }
        .grid p {
          margin: 0.2rem 0 0;
          font-size: 0.88rem;
        }
        .txs {
          list-style: none;
          margin: 0;
          padding: 0;
        }
        .txs li {
          display: grid;
          grid-template-columns: 5.5rem 4.5rem 1fr;
          gap: 0.5rem;
          padding: 0.35rem 0;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
          font-size: 0.8rem;
        }
        .txs em {
          font-style: normal;
          color: var(--ink-muted);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .atms {
          margin: 0.75rem 0 0;
          font-size: 0.78rem;
          color: var(--ink-muted);
        }
        .err {
          color: var(--warn);
          font-size: 0.85rem;
        }
      `}</style>
    </section>
  );
}
