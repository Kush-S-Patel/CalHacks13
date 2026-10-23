"use client";

import { CHAOS_BUTTONS, DEMO_SEED, formatUsd } from "@swarmcfo/shared";
import { useWorld } from "@/hooks/useWorld";
import { approve, injectChaos } from "@/lib/demo-store";

/** Owner / judge phone controller — runway + Approve + chaos inject. */
export default function PhonePage() {
  const world = useWorld();
  const waiting = world.approvals.find((a) => a.status === "waiting");

  return (
    <main className="phone">
      <p className="brand">SwarmCFO</p>
      <p className="who">{DEMO_SEED.ownerName}</p>

      <div className="runway">
        <span>Runway</span>
        <p className="mono">{world.runwayDays.toFixed(0)} days</p>
        <small className="mono">{formatUsd(world.cashBalanceCents)}</small>
      </div>

      {waiting ? (
        <button type="button" className="approve" onClick={() => approve(waiting.id)}>
          Approve {formatUsd(waiting.amountCents)}
        </button>
      ) : (
        <p className="idle">Nothing waiting — inject chaos below</p>
      )}

      <div className="chaos">
        {CHAOS_BUTTONS.map((b) => (
          <button
            key={b.kind}
            type="button"
            disabled={world.chaosInjected.includes(b.kind)}
            onClick={() => void injectChaos(b.kind)}
          >
            {b.label}
          </button>
        ))}
      </div>

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
          display: flex;
          flex-direction: column;
          gap: 0.55rem;
          margin-top: auto;
        }
        .chaos button {
          background: #1f3328;
          border: 1px solid var(--line);
          color: var(--ink);
          padding: 1rem;
          border-radius: 10px;
          font-weight: 600;
        }
        .chaos button:disabled {
          opacity: 0.45;
        }
      `}</style>
    </main>
  );
}