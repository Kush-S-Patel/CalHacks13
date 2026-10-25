"use client";

import { useWorld } from "@/hooks/useWorld";

export function RunwayHero() {
  const world = useWorld();
  const claimHolds = world.holds.filter((w) => w.kind?.startsWith("claim")).length;
  const needs = world.needsInfo.filter((w) => w.kind?.startsWith("claim")).length;
  const openClaims = world.workItems.filter((w) => w.kind?.startsWith("claim")).length;

  return (
    <header className="runway-hero">
      <div className="top">
        <div>
          <p className="brand">SwarmCFO Claims</p>
          <p className="who">
            Meridian Bookkeeping · Bay Area Workforce Collaborative · Jordan asks, Priya decides
          </p>
        </div>
      </div>
      <div className="stats">
        <article>
          <span>Open claim work</span>
          <p className="mono">{openClaims}</p>
        </article>
        <article className={needs ? "hot" : ""}>
          <span>Waiting on Priya</span>
          <p className="mono">{needs}</p>
        </article>
        <article>
          <span>Policy holds</span>
          <p className="mono">{claimHolds}</p>
        </article>
        <article>
          <span>Audit events</span>
          <p className="mono">{world.audit.length}</p>
        </article>
      </div>
      <style jsx>{`
        .runway-hero {
          padding: 2.5rem 2rem 1.25rem;
        }
        .top {
          margin-bottom: 1.25rem;
        }
        .brand {
          font-family: var(--font-display);
          font-size: clamp(2.4rem, 5.5vw, 4rem);
          font-weight: 700;
          letter-spacing: -0.03em;
          margin: 0;
          line-height: 1;
        }
        .who {
          margin: 0.45rem 0 0;
          color: var(--ink-muted);
          font-size: 1rem;
          max-width: 36rem;
        }
        .stats {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 0.65rem;
          max-width: 52rem;
        }
        @media (max-width: 700px) {
          .stats {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        article {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 0.85rem 1rem;
          background: rgba(12, 18, 16, 0.45);
        }
        article.hot {
          border-color: rgba(212, 180, 95, 0.55);
          background: rgba(80, 60, 20, 0.25);
        }
        span {
          display: block;
          font-size: 0.65rem;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--ink-muted);
          margin-bottom: 0.25rem;
        }
        p {
          margin: 0;
          font-family: var(--font-display);
          font-size: 2rem;
          font-weight: 700;
          line-height: 1;
        }
      `}</style>
    </header>
  );
}
