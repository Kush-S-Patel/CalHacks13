"use client";

import { formatUsd } from "@swarmcfo/shared";
import { useWorld } from "@/hooks/useWorld";
import { approve } from "@/lib/demo-store";

export function ApprovalPanel() {
  const { approvals } = useWorld();
  const waiting = approvals.filter((a) => a.status === "waiting");

  if (waiting.length === 0 && approvals.length === 0) return null;

  return (
    <section className="approvals">
      <h2>Owner approvals</h2>
      {waiting.length === 0 ? (
        <p className="none">No holds — Cashier is within autonomy.</p>
      ) : (
        waiting.map((a) => (
          <div key={a.id} className="row">
            <div>
              <span className="status">WAITING</span>
              <p>{a.description}</p>
              <p className="amt mono">{formatUsd(a.amountCents)}</p>
            </div>
            <button type="button" onClick={() => approve(a.id)}>
              Approve
            </button>
          </div>
        ))
      )}
      <style jsx>{`
        .approvals {
          margin: 0 2rem 2rem;
          padding: 1.25rem 1.35rem;
          border: 1px solid var(--hold);
          border-radius: 12px;
          background: rgba(201, 162, 39, 0.08);
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.15rem;
          margin: 0 0 0.75rem;
        }
        .none {
          margin: 0;
          color: var(--ink-muted);
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
          transition: transform 0.15s ease, background 0.15s ease;
        }
        button:hover {
          background: var(--accent-bright);
          transform: translateY(-1px);
        }
      `}</style>
    </section>
  );
}