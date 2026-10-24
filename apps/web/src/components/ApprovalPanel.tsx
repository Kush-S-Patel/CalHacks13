"use client";

import { formatUsd } from "@swarmcfo/shared";
import { useWorld } from "@/hooks/useWorld";
import { approve } from "@/lib/demo-store";

export function ApprovalPanel() {
  const { holds } = useWorld();
  if (holds.length === 0) return null;

  return (
    <section className="approvals">
      <h2>Owner approvals</h2>
      <p className="hint">One number. One button. Complexity under the hood.</p>
      {holds.map((a) => (
        <div key={a.id} className="row">
          <div>
            <span className="status">HELD</span>
            <p>{a.title}</p>
            <p className="amt mono">{formatUsd(a.amount_cents)}</p>
          </div>
          <button type="button" onClick={() => void approve(a.id)}>
            Approve
          </button>
        </div>
      ))}
      <style jsx>{`
        .approvals {
          margin: 0 2rem 1.5rem;
          padding: 1.25rem 1.35rem;
          border: 1px solid var(--hold);
          border-radius: 12px;
          background: rgba(201, 162, 39, 0.08);
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.15rem;
          margin: 0;
        }
        .hint {
          margin: 0.25rem 0 0.85rem;
          color: var(--ink-muted);
          font-size: 0.85rem;
        }
        .row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
        }
        .status {
          font-size: 0.7rem;
          font-weight: 700;
          letter-spacing: 0.12em;
          color: var(--hold);
        }
        p {
          margin: 0.25rem 0 0;
        }
        .amt {
          font-size: 1.25rem;
          font-weight: 600;
        }
        button {
          border: none;
          background: var(--accent);
          color: #04140c;
          font-weight: 700;
          font-size: 1rem;
          padding: 0.85rem 1.4rem;
          border-radius: 8px;
        }
      `}</style>
    </section>
  );
}