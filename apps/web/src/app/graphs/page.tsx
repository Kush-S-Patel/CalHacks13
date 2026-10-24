"use client";

import Link from "next/link";
import { useEffect } from "react";
import { GraphSuite } from "@/components/graphs/GraphSuite";
import { refresh, injectChaos } from "@/lib/demo-store";
import { useWorld } from "@/hooks/useWorld";
import { formatUsd } from "@swarmcfo/shared";

/** Full-bleed graph stage for judges — supply chain / context / relationships. */
export default function GraphsPage() {
  const world = useWorld();

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <main className="stage">
      <header>
        <div>
          <p className="brand">SwarmCFO</p>
          <h1>Context & supply chain</h1>
          <p className="sub">
            Complicated company, one shared world — exact dollars on every edge. Fraud in red.
            Holds in amber.
          </p>
        </div>
        <div className="side">
          <p className="mono runway">{world.runwayDays.toFixed(0)} days</p>
          <p className="mono muted">{formatUsd(world.cashBalanceCents)}</p>
          <button type="button" onClick={() => void injectChaos()}>
            Run chaos (update graphs)
          </button>
          <Link href="/">Back to world</Link>
        </div>
      </header>
      <GraphSuite />
      <style jsx>{`
        .stage {
          min-height: 100dvh;
          padding-bottom: 2rem;
        }
        header {
          display: flex;
          justify-content: space-between;
          gap: 1.5rem;
          padding: 2rem 2rem 1rem;
          align-items: flex-end;
        }
        .brand {
          font-family: var(--font-display);
          font-size: 1.5rem;
          font-weight: 700;
          margin: 0;
        }
        h1 {
          font-family: var(--font-display);
          font-size: clamp(1.8rem, 4vw, 2.6rem);
          margin: 0.25rem 0;
          font-weight: 700;
        }
        .sub {
          margin: 0;
          color: var(--ink-muted);
          max-width: 34rem;
        }
        .side {
          text-align: right;
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.35rem;
        }
        .runway {
          font-family: var(--font-display);
          font-size: 2.5rem;
          font-weight: 700;
          margin: 0;
          color: var(--accent-bright);
        }
        .muted {
          margin: 0;
          color: var(--ink-muted);
        }
        button {
          margin-top: 0.35rem;
          border: 1px solid var(--accent);
          background: #1f3328;
          color: var(--ink);
          padding: 0.55rem 0.9rem;
          border-radius: 8px;
          font-weight: 600;
        }
        .side :global(a) {
          font-size: 0.8rem;
          color: var(--ink-muted);
        }
      `}</style>
    </main>
  );
}