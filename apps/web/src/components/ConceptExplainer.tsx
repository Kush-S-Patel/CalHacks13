"use client";

import { useWorld } from "@/hooks/useWorld";

export function ConceptExplainer() {
  const world = useWorld();
  const waiting = world.needsInfo.filter((w) => w.kind?.startsWith("claim")).length;
  const holds = world.holds.filter((w) => w.kind?.startsWith("claim")).length;

  return (
    <section id="how-it-works" className="explain">
      <div className="block">
        <h2>The corner we own</h2>
        <p>
          Outsourced bookkeepers assemble the same federal reimbursement package every month: match
          GL lines to receipts, catch duplicates and period mistakes, decide what is allowable, then
          hand a clean package to a finance manager. Agencies pay slowly; mistakes cost weeks. We do
          not replace the grant portal — we are the <strong>system of work</strong> on top of it.
        </p>
      </div>

      <div className="trio">
        <article>
          <span>01 · Ask</span>
          <h3>Ambiguity stops the machine</h3>
          <p>
            Jordan (Claims Agent) prepares September for Bay Area Workforce Collaborative. Four
            problems appear. The $860 catering charge is unclear — so the agent <em>asks Priya</em>,
            instead of guessing entertainment vs program cost.
          </p>
        </article>
        <article>
          <span>02 · Learn</span>
          <h3>A no becomes memory</h3>
          <p>
            Priya says no — staff celebration, exclude it. That correction becomes a{" "}
            <strong>precedent</strong>, then a standing <strong>policy</strong> she approves. October’s
            similar catering is auto-held before it enters a claim.
          </p>
        </article>
        <article>
          <span>03 · Prove</span>
          <h3>Limits in code, not prompts</h3>
          <p>
            Jordan cannot approve the package — that attempt is <strong>DENIED</strong> and audited.
            Only Priya approves. The system never submits to the funder and never alters the ledger.
            Every transition keeps a diff.
          </p>
        </article>
      </div>

      <div className="proof">
        <h2>What “done” looks like</h2>
        <ul>
          <li>
            <strong>$8,160</strong> kept off the award
          </li>
          <li>
            <strong>$124</strong> receipt attached
          </li>
          <li>
            <strong>$28,135</strong> eligible reimbursement
          </li>
          <li>
            Critical exceptions <strong>4 → 0</strong>
          </li>
          <li>
            Unauthorized approvals <strong>0</strong>
          </li>
        </ul>
        <p className="live">
          Live board · waiting on Priya <span className="mono">{waiting}</span> · policy holds{" "}
          <span className="mono">{holds}</span> · audit{" "}
          <span className="mono">{world.audit.length}</span>
        </p>
      </div>

      <style jsx>{`
        .explain {
          padding: 2.5rem clamp(1.25rem, 4vw, 2.5rem) 1rem;
          max-width: 1100px;
        }
        .block {
          max-width: 40rem;
          margin-bottom: 2rem;
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.55rem;
          margin: 0 0 0.55rem;
        }
        .block p {
          margin: 0;
          color: var(--ink-muted);
          line-height: 1.55;
          font-size: 1rem;
        }
        .block strong {
          color: var(--ink);
          font-weight: 600;
        }
        .trio {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 1.25rem;
          margin-bottom: 2.25rem;
        }
        @media (max-width: 800px) {
          .trio {
            grid-template-columns: 1fr;
          }
        }
        article span {
          display: block;
          font-size: 0.68rem;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--accent-bright);
          margin-bottom: 0.4rem;
        }
        article h3 {
          font-family: var(--font-display);
          font-size: 1.15rem;
          margin: 0 0 0.45rem;
          font-weight: 600;
        }
        article p {
          margin: 0;
          color: var(--ink-muted);
          font-size: 0.9rem;
          line-height: 1.5;
        }
        .proof {
          border-top: 1px solid var(--line);
          padding-top: 1.5rem;
        }
        .proof ul {
          list-style: none;
          margin: 0.75rem 0 1rem;
          padding: 0;
          display: flex;
          flex-wrap: wrap;
          gap: 0.55rem 1.25rem;
        }
        .proof li {
          font-size: 0.92rem;
          color: var(--ink-muted);
        }
        .proof strong {
          color: var(--accent-bright);
          font-family: var(--font-display);
          font-size: 1.05rem;
        }
        .live {
          margin: 0;
          font-size: 0.82rem;
          color: var(--ink-muted);
        }
        .live .mono {
          color: var(--ink);
          font-weight: 600;
        }
      `}</style>
    </section>
  );
}
