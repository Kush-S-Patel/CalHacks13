"use client";

import { useEffect } from "react";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { AuditTrail } from "@/components/AuditTrail";
import { ChaosButtons } from "@/components/ChaosButtons";
import { ConceptBanner } from "@/components/ConceptBanner";
import { ConceptExplainer } from "@/components/ConceptExplainer";
import { JoinQr } from "@/components/JoinQr";
import { PolicyPanel } from "@/components/PolicyPanel";
import { WorkQueue } from "@/components/WorkQueue";
import { NessieBadge } from "@/components/NessieBadge";
import { refresh } from "@/lib/demo-store";
import Link from "next/link";

/** Claims demo homepage — concept → explainer → live learning loop → proof surfaces. */
export default function WorldPage() {
  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 4000);
    return () => clearInterval(t);
  }, []);

  return (
    <main>
      <ConceptBanner />
      <nav className="subnav">
        <Link href="/demo">Open guided claim review</Link>
        <Link href="#how-it-works">How it works</Link>
        <Link href="#live-demo">Live demo</Link>
        <Link href="/suite/claims">Claims suite</Link>
        <Link href="/suite">ERP</Link>
        <NessieBadge compact />
      </nav>
      <ConceptExplainer />
      <ChaosButtons />
      <section className="proof-strip">
        <h2>Proof surfaces</h2>
        <p>After you run the loop, these panels show the same work as governed state — not a separate product.</p>
      </section>
      <WorkQueue />
      <ApprovalPanel />
      <PolicyPanel />
      <AuditTrail />
      <JoinQr />
      <style jsx>{`
        .subnav {
          padding: 0.85rem clamp(1.25rem, 4vw, 2.5rem);
          display: flex;
          gap: 1.1rem;
          flex-wrap: wrap;
          border-bottom: 1px solid var(--line);
          background: rgba(8, 12, 10, 0.55);
          position: sticky;
          top: 0;
          z-index: 5;
          backdrop-filter: blur(10px);
        }
        .subnav :global(a) {
          font-size: 0.85rem;
          color: var(--accent-bright);
          border-bottom: 1px solid transparent;
        }
        .subnav :global(a:hover) {
          border-bottom-color: var(--accent-bright);
        }
        .proof-strip {
          padding: 1.5rem clamp(1.25rem, 4vw, 2.5rem) 0.25rem;
          max-width: 40rem;
        }
        .proof-strip h2 {
          font-family: var(--font-display);
          font-size: 1.25rem;
          margin: 0 0 0.35rem;
        }
        .proof-strip p {
          margin: 0;
          color: var(--ink-muted);
          font-size: 0.92rem;
          line-height: 1.45;
        }
      `}</style>
    </main>
  );
}
