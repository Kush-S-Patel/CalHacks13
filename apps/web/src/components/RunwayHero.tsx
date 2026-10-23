"use client";

import { DEMO_SEED, formatUsd } from "@swarmcfo/shared";
import { useWorld } from "@/hooks/useWorld";

export function RunwayHero() {
  const world = useWorld();
  const improved = world.runwayDays > DEMO_SEED.runwayDays + 0.5;

  return (
    <header className="runway-hero">
      <p className="brand">SwarmCFO</p>
      <p className="who">
        {DEMO_SEED.ownerName} · {DEMO_SEED.businessName}
      </p>
      <div className="runway-block">
        <span className="label">Cash runway</span>
        <p className={`days mono ${improved ? "up" : ""}`}>
          {world.runwayDays.toFixed(0)}
          <span className="unit"> days</span>
        </p>
        <p className="cash mono">
          {formatUsd(world.cashBalanceCents)} · burns {formatUsd(world.dailyBurnCents)}/day
        </p>
      </div>
      <style jsx>{`
        .runway-hero {
          padding: 2.5rem 2rem 1.5rem;
        }
        .brand {
          font-family: var(--font-display);
          font-size: clamp(2.5rem, 6vw, 4.5rem);
          font-weight: 700;
          letter-spacing: -0.03em;
          margin: 0;
          line-height: 1;
        }
        .who {
          margin: 0.4rem 0 2rem;
          color: var(--ink-muted);
          font-size: 1rem;
        }
        .label {
          display: block;
          text-transform: uppercase;
          letter-spacing: 0.14em;
          font-size: 0.72rem;
          color: var(--ink-muted);
          margin-bottom: 0.35rem;
        }
        .days {
          font-family: var(--font-display);
          font-size: clamp(4rem, 12vw, 7rem);
          font-weight: 700;
          margin: 0;
          line-height: 0.95;
          transition: color 0.4s ease;
        }
        .days.up {
          color: var(--accent-bright);
        }
        .unit {
          font-size: 0.35em;
          font-weight: 500;
          color: var(--ink-muted);
        }
        .cash {
          margin: 0.75rem 0 0;
          color: var(--ink-muted);
          font-size: 1.05rem;
        }
      `}</style>
    </header>
  );
}