"use client";

import { AGENT_LABELS, formatUsd, type AgentName } from "@swarmcfo/shared";
import { useWorld } from "@/hooks/useWorld";

export function ActionFeed() {
  const { actions } = useWorld();

  return (
    <section className="feed">
      <h2>Auditable actions</h2>
      <p className="sub">Not a chat transcript — every row is a reducer call.</p>
      <ul>
        {actions.length === 0 && <li className="empty">Waiting for chaos…</li>}
        {actions.map((a) => (
          <li key={a.id}>
            <span className={`badge ${a.actionType}`}>{a.actionType.toUpperCase()}</span>
            <div>
              <strong>
                {a.agent in AGENT_LABELS
                  ? AGENT_LABELS[a.agent as AgentName]
                  : a.agent}
              </strong>
              <p>{a.rationale}</p>
              {a.amountCents > 0 && <span className="amt mono">{formatUsd(a.amountCents)}</span>}
            </div>
          </li>
        ))}
      </ul>
      <style jsx>{`
        .feed {
          padding: 0 2rem 2rem;
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.4rem;
          margin: 0 0 0.25rem;
        }
        .sub {
          margin: 0 0 1rem;
          color: var(--ink-muted);
          font-size: 0.9rem;
        }
        ul {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 0.65rem;
          max-height: 48vh;
          overflow: auto;
        }
        li {
          display: grid;
          grid-template-columns: 6.5rem 1fr;
          gap: 0.75rem;
          padding: 0.85rem 1rem;
          background: rgba(26, 42, 34, 0.75);
          border: 1px solid var(--line);
          border-radius: 10px;
          animation: in 0.35s ease;
        }
        .empty {
          display: block;
          color: var(--ink-muted);
          border-style: dashed;
        }
        .badge {
          align-self: start;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.06em;
          padding: 0.35rem 0.45rem;
          border-radius: 4px;
          text-align: center;
          background: var(--bg-deep);
        }
        .badge.block {
          color: var(--danger);
        }
        .badge.counter,
        .badge.chase,
        .badge.defer,
        .badge.announce {
          color: var(--accent-bright);
        }
        .badge.hold {
          color: var(--hold);
        }
        .badge.approve {
          color: var(--accent);
        }
        .badge.arbitrate,
        .badge.flag {
          color: var(--warn);
        }
        strong {
          font-size: 0.85rem;
        }
        p {
          margin: 0.2rem 0 0;
          font-size: 0.88rem;
          color: var(--ink-muted);
          line-height: 1.35;
        }
        .amt {
          display: inline-block;
          margin-top: 0.35rem;
          font-size: 0.8rem;
          color: var(--ink);
        }
        @keyframes in {
          from {
            opacity: 0;
            transform: translateY(6px);
          }
          to {
            opacity: 1;
            transform: none;
          }
        }
      `}</style>
    </section>
  );
}