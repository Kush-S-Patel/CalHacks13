"use client";

import { useEffect } from "react";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { AuditTrail } from "@/components/AuditTrail";
import { ChaosButtons } from "@/components/ChaosButtons";
import { PolicyPanel } from "@/components/PolicyPanel";
import { ScoreCard } from "@/components/ScoreCard";
import { WorkQueue } from "@/components/WorkQueue";
import { refresh } from "@/lib/demo-store";

export default function SuiteWorkPage() {
  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div>
      <ScoreCard />
      <ChaosButtons />
      <ApprovalPanel />
      <WorkQueue />
      <PolicyPanel />
      <AuditTrail />
    </div>
  );
}