"use client";

import { useWorld } from "@/hooks/useWorld";

export function AuditTrail() {
  const { actions } = useWorld();

  return (
    <section className="audit">
      <h2>Audit trail</h2>
      <p className="sub">
        Append-only diffs. Denied attempts logged too. Claim question → answer → revision → policy →
        DENIED agent approve → finance manager approve.
      </p>
      <ul>
        {actions.length === 0 && <li className="empty">No events yet — run the Claims learning loop.</li>}
        {actions.map((a) => (
          <li key={a.id} className={a.allowed === false ? "denied" : ""}>
            <span className="act">{a.actionType}</span>
            <div>
              <strong>{a.agent}</strong>
              <p>
                {a.targetId}: {a.rationale}
              </p>
              {a.allowed === false && <em>DENIED</em>}
              {a.diff && Object.keys(a.diff).length > 0 && (
                <pre className="diff">{formatDiff(a.diff)}</pre>
              )}
            </div>
          </li>
        ))}
      </ul>
      <style jsx>{`
        .audit {
          padding: 0 2rem 2.5rem;
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.25rem;
          margin: 0 0 0.25rem;
        }
        .sub {
          margin: 0 0 0.85rem;
          color: var(--ink-muted);
          font-size: 0.88rem;
        }
        ul {
          list-style: none;
          margin: 0;
          padding: 0;
          max-height: 40vh;
          overflow: auto;
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
        }
        li {
          display: grid;
          grid-template-columns: 5.5rem 1fr;
          gap: 0.6rem;
          padding: 0.55rem 0.75rem;
          border-left: 2px solid var(--accent);
          background: rgba(26, 42, 34, 0.45);
          font-size: 0.82rem;
        }
        li.denied {
          border-left-color: var(--danger);
        }
        .empty {
          display: block;
          color: var(--ink-muted);
          border: none;
        }
        .act {
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          color: var(--ink-muted);
        }
        p {
          margin: 0.15rem 0 0;
          color: var(--ink-muted);
        }
        em {
          color: var(--danger);
          font-style: normal;
          font-size: 0.72rem;
          font-weight: 700;
        }
        .diff {
          margin: 0.35rem 0 0;
          font-size: 0.65rem;
          line-height: 1.35;
          max-height: 4.5rem;
          overflow: auto;
          background: rgba(0, 0, 0, 0.35);
          padding: 0.35rem 0.45rem;
          border-radius: 4px;
          color: #b8cfc4;
          white-space: pre-wrap;
        }
      `}</style>
    </section>
  );
}

function formatDiff(diff: Record<string, unknown>): string {
  try {
    const parts: string[] = [];
    for (const [k, v] of Object.entries(diff)) {
      if (v && typeof v === "object" && "from" in (v as object) && "to" in (v as object)) {
        const d = v as { from: unknown; to: unknown };
        parts.push(`${k}: ${JSON.stringify(d.from)} → ${JSON.stringify(d.to)}`);
      } else {
        parts.push(`${k}: ${JSON.stringify(v).slice(0, 120)}`);
      }
    }
    return parts.slice(0, 6).join("\n");
  } catch {
    return "";
  }
}
