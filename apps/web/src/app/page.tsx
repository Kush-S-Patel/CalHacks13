"use client";

import { useEffect } from "react";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { AuditTrail } from "@/components/AuditTrail";
import { ChaosButtons } from "@/components/ChaosButtons";
import { JoinQr } from "@/components/JoinQr";
import { PolicyPanel } from "@/components/PolicyPanel";
import { RunwayHero } from "@/components/RunwayHero";
import { ScoreCard } from "@/components/ScoreCard";
import { WorkQueue } from "@/components/WorkQueue";
import { GraphSuite } from "@/components/graphs/GraphSuite";
import { NessieBadge } from "@/components/NessieBadge";
import { NessiePanel } from "@/components/NessiePanel";
import { refresh } from "@/lib/demo-store";
import Link from "next/link";

/** Big-screen system of work — runway, graphs, queue, policies, audit, score. */
export default function WorldPage() {
  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 4000);
    return () => clearInterval(t);
  }, []);

  return (
    <main>
      <RunwayHero />
      <nav className="subnav">
        <Link href="/suite/claims">Claims + risk</Link>
        <Link href="/suite">ERP Suite</Link>
        <Link href="/suite/jobs">Jobs</Link>
        <Link href="/suite/upload">Upload sheets</Link>
        <Link href="/graphs">Graph stage</Link>
        <NessieBadge compact />
      </nav>
      <ScoreCard />
      <ChaosButtons />
      <NessiePanel />
      <GraphSuite compact />
      <ApprovalPanel />
      <WorkQueue />
      <PolicyPanel />
      <AuditTrail />
      <JoinQr />
      <style jsx>{`
        .subnav {
          padding: 0 2rem 0.75rem;
          display: flex;
          gap: 1rem;
          flex-wrap: wrap;
        }
        .subnav :global(a) {
          font-size: 0.85rem;
          color: var(--accent-bright);
          border-bottom: 1px solid transparent;
        }
        .subnav :global(a:hover) {
          border-bottom-color: var(--accent-bright);
        }
      `}</style>
    </main>
  );
}