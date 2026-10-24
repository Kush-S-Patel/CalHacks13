"use client";

import { DEMO_SEED, formatUsd } from "@swarmcfo/shared";
import { useEffect } from "react";
import { useWorld } from "@/hooks/useWorld";
import { approve, injectChaos, refresh } from "@/lib/demo-store";

/** Owner phone — runway + Approve + run demo. */
export default function PhonePage() {
  const world = useWorld();
  const hold = world.holds[0];

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <main className="phone">
      <p className="brand">SwarmCFO</p>
      <p className="who">{DEMO_SEED.ownerName} · system of work</p>

      <div className="runway">
        <span>Runway</span>
        <p className="mono">{world.runwayDays.toFixed(0)} days</p>
        <small className="mono">{formatUsd(world.cashBalanceCents)}</small>
        {world.score && (
          <small className="score">Hyphenate {world.score.hyphenate_score}/100</small>
        )}
      </div>

      {hold ? (
        <button type="button" className="approve" onClick={() => void approve(hold.id)}>
          Approve {formatUsd(hold.amount_cents)}
        </button>
      ) : (
        <p className="idle">Nothing held — run chaos to open work</p>
      )}

      <button type="button" className="chaos" onClick={() => void injectChaos()}>
        Run full demo
      </button>

      <style jsx>{`
        .phone {
          min-height: 100dvh;
          padding: 1.75rem 1.25rem 2.5rem;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }
        .brand {
          font-family: var(--font-display);
          font-size: 1.75rem;
          font-weight: 700;
          margin: 0;
        }
        .who {
          margin: -0.75rem 0 0;
          color: var(--ink-muted);
        }
        .runway {
          padding: 1.5rem;
          background: var(--bg-panel);
          border-radius: 16px;
          border: 1px solid var(--line);
        }
        .runway span {
          text-transform: uppercase;
          letter-spacing: 0.12em;
          font-size: 0.7rem;
          color: var(--ink-muted);
        }
        .runway p {
          font-family: var(--font-display);
          font-size: 3.5rem;
          font-weight: 700;
          margin: 0.2rem 0;
          line-height: 1;
        }
        small {
          color: var(--ink-muted);
          display: block;
        }
        .score {
          margin-top: 0.5rem;
          color: var(--accent-bright) !important;
        }
        .approve {
          border: none;
          background: var(--accent);
          color: #04140c;
          font-weight: 700;
          font-size: 1.15rem;
          padding: 1.15rem;
          border-radius: 12px;
          width: 100%;
        }
        .idle {
          margin: 0;
          color: var(--ink-muted);
          text-align: center;
          font-size: 0.9rem;
        }
        .chaos {
          margin-top: auto;
          background: #1f3328;
          border: 1px solid var(--line);
          color: var(--ink);
          padding: 1rem;
          border-radius: 10px;
          font-weight: 600;
        }
      `}</style>
    </main>
  );
}