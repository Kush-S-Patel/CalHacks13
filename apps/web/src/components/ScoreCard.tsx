"use client";

import { useWorld } from "@/hooks/useWorld";

export function ScoreCard() {
  const { score } = useWorld();
  if (!score) return null;

  return (
    <section className="score">
      <div className="num mono">{score.hyphenate_score}</div>
      <div>
        <h2>Hyphenate score</h2>
        <p className="sub">Limits in code · audit of every call · self-learning policies</p>
        <ul>
          {Object.entries(score.judging).map(([k, v]) => (
            <li key={k} className={v ? "ok" : "no"}>
              {v ? "PASS" : "GAP"} · {k.replace(/_/g, " ")}
            </li>
          ))}
        </ul>
      </div>
      <style jsx>{`
        .score {
          margin: 0 2rem 1.5rem;
          padding: 1.25rem 1.4rem;
          display: grid;
          grid-template-columns: auto 1fr;
          gap: 1.25rem;
          align-items: center;
          background: rgba(61, 155, 106, 0.1);
          border: 1px solid rgba(95, 212, 154, 0.35);
          border-radius: 14px;
        }
        .num {
          font-family: var(--font-display);
          font-size: 3.5rem;
          font-weight: 700;
          color: var(--accent-bright);
          line-height: 1;
        }
        h2 {
          font-family: var(--font-display);
          margin: 0 0 0.2rem;
          font-size: 1.15rem;
        }
        .sub {
          margin: 0 0 0.6rem;
          color: var(--ink-muted);
          font-size: 0.85rem;
        }
        ul {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
        }
        li {
          font-size: 0.72rem;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          background: var(--bg-deep);
        }
        li.ok {
          color: var(--accent-bright);
        }
        li.no {
          color: var(--danger);
        }
      `}</style>
    </section>
  );
}