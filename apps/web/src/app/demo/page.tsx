import type { Metadata } from "next";
import { ClaimDemo } from "@/components/demo/ClaimDemo";

export const metadata: Metadata = {
  title: "SwarmCFO Claims — Guided Review",
  description: "Evidence-backed grant reimbursement review with human approval boundaries.",
};

export default function DemoPage() {
  return <ClaimDemo />;
}
