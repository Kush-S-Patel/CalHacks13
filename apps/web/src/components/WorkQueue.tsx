"use client";

import { formatUsd } from "@swarmcfo/shared";
import { useWorld } from "@/hooks/useWorld";
import { approve, answer, reject } from "@/lib/demo-store";

const STATE_COLOR: Record<string, string> = {
  NEW: "var(--ink-muted)",
  PROPOSED: "var(--warn)",
  NEEDS_INFO: "var(--hold)",
  HELD: "var(--hold)",
  BLOCKED: "var(--danger)",
  APPROVED: "var(--accent)",
  REJECTED: "var(--danger)",
  POSTED: "var(--accent-bright)",
};

export function WorkQueue() {
  const { workItems, needsInfo, holds } = useWorld();
  const active = [...holds, ...needsInfo, ...workItems.filter((w) => !["POSTED", "REJECTED"].includes(w.state))];
  const seen = new Set<string>();
  const rows = active.filter((w) => (seen.has(w.id) ? false : (seen.add(w.id), true))).slice(0, 12);

  return (
    <section className="queue">
      <h2>Work queue</h2>
      <p className="sub">System of work — not a chat. Every row is a state machine.</p>
      <ul>
        {rows.length === 0 && <li className="empty">Run the demo to open work items.</li>}
        {rows.map((w) => (
          <li key={w.id}>
            <span className="state" style={{ color: STATE_COLOR[w.state] ?? "inherit" }}>
              {w.state}
            </span>
            <div className="body">
              <strong>
                {w.kind} · {w.title}
              </strong>
              <p>
                {w.subject}
                {w.amount_cents > 0 ? ` · ${formatUsd(w.amount_cents)}` : ""}
                {w.policy_id ? ` · ${w.policy_id}` : ""}
              </p>
              {w.question && <p className="q">Ask: {w.question}</p>}
              <div className="actions">
                {w.state === "HELD" || w.state === "PROPOSED" ? (
                  <>
                    <button type="button" onClick={() => void approve(w.id)}>
                      Approve
                    </button>
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => void reject(w.id, "No - owner rejected")}
                    >
                      Reject
                    </button>
                  </>
                ) : null}
                {w.state === "NEEDS_INFO" ? (
                  <button
                    type="button"
                    onClick={() => void answer(w.id, "Book it - intermediary fee.")}
                  >
                    Answer
                  </button>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ul>
      <style jsx>{`
        .queue {
          padding: 0 2rem 1.5rem;
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.35rem;
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
          gap: 0.55rem;
          max-height: 42vh;
          overflow: auto;
        }
        li {
          display: grid;
          grid-template-columns: 7rem 1fr;
          gap: 0.75rem;
          padding: 0.85rem 1rem;
          background: rgba(26, 42, 34, 0.75);
          border: 1px solid var(--line);
          border-radius: 10px;
        }
        .empty {
          display: block;
          color: var(--ink-muted);
          border-style: dashed;
        }
        .state {
          font-size: 0.68rem;
          font-weight: 700;
          letter-spacing: 0.08em;
        }
        strong {
          font-size: 0.9rem;
        }
        p {
          margin: 0.2rem 0 0;
          font-size: 0.82rem;
          color: var(--ink-muted);
        }
        .q {
          color: var(--hold) !important;
        }
        .actions {
          display: flex;
          gap: 0.4rem;
          margin-top: 0.5rem;
        }
        button {
          border: none;
          background: var(--accent);
          color: #04140c;
          font-weight: 700;
          font-size: 0.8rem;
          padding: 0.45rem 0.75rem;
          border-radius: 6px;
        }
        button.ghost {
          background: transparent;
          border: 1px solid var(--line);
          color: var(--ink-muted);
        }
      `}</style>
    </section>
  );
}