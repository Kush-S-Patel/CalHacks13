import { ActionFeed } from "@/components/ActionFeed";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { ChaosButtons } from "@/components/ChaosButtons";
import { JoinQr } from "@/components/JoinQr";
import { RunwayHero } from "@/components/RunwayHero";

/** Big-screen world view — one number (runway) + live auditable actions. */
export default function WorldPage() {
  return (
    <main>
      <RunwayHero />
      <ChaosButtons />
      <ApprovalPanel />
      <ActionFeed />
      <JoinQr />
    </main>
  );
}