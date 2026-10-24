"use client";

import { useWorld } from "@/hooks/useWorld";

export function PolicyPanel() {
  const { policies } = useWorld();
  if (policies.length === 0) return null;

  return (
    <section className="policies">
      <h2>Learned policies</h2>
      <p className="sub">TIME — survives the context window. Drafted from history, approved by Maya.</p>
      <ul>
        {policies.map((p) => (
          <li key={`${p.id}-v${p.version}`}>
            <span className={`st ${p.status}`}>{p.status}</span>
            <div>
              <strong>
                {p.id} · {p.title}
              </strong>
              <p>{p.rule}</p>
              <small>{p.evidence?.length ?? 0} evidence refs</small>
            </div>
          </li>
        ))}
      </ul>
      <style jsx>{`
        .policies {
          padding: 0 2rem 1.5rem;
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
          display: grid;
          gap: 0.5rem;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        }
        li {
          display: grid;
          grid-template-columns: 5.5rem 1fr;
          gap: 0.6rem;
          padding: 0.75rem 0.9rem;
          border: 1px solid var(--line);
          border-radius: 10px;
          background: rgba(12, 18, 16, 0.5);
        }
        .st {
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }
        .st.active {
          color: var(--accent-bright);
        }
        .st.needs_approval {
          color: var(--hold);
        }
        p {
          margin: 0.25rem 0;
          font-size: 0.82rem;
          color: var(--ink-muted);
        }
        small {
          color: var(--ink-muted);
          font-size: 0.72rem;
        }
      `}</style>
    </section>
  );
}