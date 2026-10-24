"use client";

import { useEffect } from "react";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { AuditTrail } from "@/components/AuditTrail";
import { ChaosButtons } from "@/components/ChaosButtons";
import { JoinQr } from "@/components/JoinQr";
import { PolicyPanel } from "@/components/PolicyPanel";
import { RunwayHero } from "@/components/RunwayHero";
import { WorkQueue } from "@/components/WorkQueue";
import { NessieBadge } from "@/components/NessieBadge";
import { refresh } from "@/lib/demo-store";
import Link from "next/link";

/** Claims-first Hyphenate surface — learning loop leads; bakery SoW is secondary. */
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
        <Link href="/suite/claims">Claims suite</Link>
        <Link href="/suite">ERP</Link>
        <Link href="/suite/jobs">Jobs</Link>
        <NessieBadge compact />
      </nav>
      <ChaosButtons />
      <WorkQueue />
      <ApprovalPanel />
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
