"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import styles from "./ClaimDemo.module.css";

const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

type Match = {
  ledger_id: string;
  description: string;
  amount_cents: number;
  date: string;
  vendor: string;
  budget_line: string;
  evidence_ids: string[];
  confidence: number;
  exception_codes: string[];
};

type Evidence = {
  id: string;
  kind: string;
  filename: string;
  linked_ledger_id?: string | null;
};

type RuleSource = {
  title?: string;
  url?: string;
  quote?: string;
  provenance?: string;
  live_refresh?: boolean;
  apify_run_id?: string;
  fetched_at?: string;
};

type ProviderReceipts = {
  apify?: { run_id?: string; dataset_id?: string; actor_id?: string; source_url?: string; title?: string; fetched_at?: string };
  claude?: { confidence?: number; error?: string; message?: string; rule?: string; exact_quote?: string; suggested_question?: string; needs_human?: boolean; model?: string };
};

type PolicyMatchBasis = {
  matcher?: string;
  matched_terms?: string[];
  policy_id?: string;
};

type GuidedFlow = {
  phase?: string;
  decision?: {
    ledger_id?: string;
    decision?: "exclude" | "keep";
    reason?: string;
    actor?: string;
  } | null;
  resolved_exceptions?: Array<{
    ledger_id?: string;
    action?: string;
    reason?: string;
  }>;
  policy_id?: string | null;
  policy_status?: string | null;
  future_claim_id?: string | null;
  future_claim_work_item_id?: string | null;
  future_claim_policy_id?: string | null;
  future_claim_policy_version?: number | null;
  future_claim_reporting_period?: string | null;
  future_claim_match_basis?: string | PolicyMatchBasis | null;
  ai_approval_receipt?: { denied?: boolean; authorization_reason?: string } | null;
  manager_approval?: { actor?: string; reason?: string } | null;
};

type HeldWorkItem = {
  id?: string;
  state?: string;
  title?: string;
  kind?: string;
  amount_cents?: number;
  policy_id?: string;
};

type Claim = {
  id: string;
  nonprofit: string;
  reporting_period: string;
  status: string;
  award: {
    award_id: string;
    funder: string;
    cfda: string;
  };
  matches: Match[];
  evidence: Evidence[];
  totals: Record<string, number>;
  exceptions: Array<{ code?: string; ledger_id?: string; message?: string }>;
  meta?: {
    revision?: number;
    rule_source?: RuleSource;
    guided_flow?: GuidedFlow;
    excluded?: Array<{ ledger_id: string; reason: string; amount_cents: number }>;
    provider_receipts?: ProviderReceipts;
    rule_refresh?: { status?: string; apify_run_id?: string; suggested_question?: string; error?: string };
    [key: string]: unknown;
  };
};

type StoryStep = {
  step?: number;
  actor?: string;
  action?: string;
  spoken?: string;
  detail?: string | string[];
};

type DemoResponse = {
  ok?: boolean;
  phase?: string;
  awaiting_manager?: boolean;
  claim_id?: string;
  question?: string;
  claim?: Claim;
  story?: StoryStep[];
  results?: Record<string, unknown>;
  audit?: Array<Record<string, unknown>>;
  policy?: { id?: string; version?: number; status?: string; title?: string; rule?: string };
  denials?: Array<Record<string, unknown>>;
  unresolved_exceptions?: Array<{ code?: string; ledger_id?: string; message?: string }>;
  denial_receipt?: { denied?: boolean; authorization_reason?: string };
  future_claim?: Claim;
  future_claim_work_item?: HeldWorkItem;
  work_item?: HeldWorkItem;
  workflow?: { future_claim_work_item?: HeldWorkItem };
  match_basis?: string | PolicyMatchBasis;
};

type PendingResponse = {
  active?: {
    claim_id: string;
    question?: string;
    awaiting_manager?: boolean;
    claim?: Claim;
  };
};

const stages = [
  "Source attached",
  "Rule interpreted",
  "Claim checked",
  "Human decision",
  "Policy learned",
  "Approval proven",
];

const statusCopy: Record<string, string> = {
  missing_receipt: "Receipt needed",
  missing_payroll: "Payroll support needed",
  duplicate_expense: "Possible duplicate",
  period_of_performance: "Outside reporting month",
  ineligible_participant: "Needs judgment",
  unreconciled_gl: "Reconciliation hold",
  excluded_from_claim: "Excluded",
};

const issuePriority = [
  "excluded_from_claim",
  "ineligible_participant",
  "duplicate_expense",
  "period_of_performance",
  "missing_receipt",
  "missing_payroll",
  "unreconciled_gl",
];

const phaseCopy: Record<
  string,
  { status: string; reasonLabel: string; reasonHelp: string; metric: string }
> = {
  awaiting_decision: {
    status: "Decision needed",
    reasonLabel: "Decision reason",
    reasonHelp: "Required. The reason is preserved in the audit record and future rule proposal.",
    metric: "Before manager decision",
  },
  decision_recorded: {
    status: "Resolve exceptions",
    reasonLabel: "Resolution reason",
    reasonHelp: "Resolve only the selected line; every other exception remains blocked.",
    metric: "Decision recorded",
  },
  ready_for_policy: {
    status: "Policy ready",
    reasonLabel: "Policy proposal reason",
    reasonHelp: "Proposing a reusable rule does not activate it.",
    metric: "All line exceptions resolved",
  },
  policy_pending_approval: {
    status: "Policy approval needed",
    reasonLabel: "Policy approval reason",
    reasonHelp: "A finance manager must review the proposed rule as a separate action.",
    metric: "Claim ready; rule pending",
  },
  policy_active: {
    status: "New claim test",
    reasonLabel: "Submission reason",
    reasonHelp: "Create a separate October claim to prove the approved rule applies beyond its source case.",
    metric: "Policy active",
  },
  future_claim_held: {
    status: "New claim held",
    reasonLabel: "Approval request context",
    reasonHelp: "The learned rule held an independent claim; now test the manager-only approval boundary.",
    metric: "Independent claim held",
  },
  ai_approval_denied: {
    status: "Manager approval needed",
    reasonLabel: "Manager approval reason",
    reasonHelp: "The automated actor was denied; an authorized manager may approve the clean package.",
    metric: "Automated approval blocked",
  },
  approved: {
    status: "Approved package",
    reasonLabel: "Approval reason",
    reasonHelp: "The final manager decision is preserved in the audit trail.",
    metric: "Ready for filing",
  },
};

function money(cents?: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format((cents ?? 0) / 100);
}

function lineStatus(match: Match) {
  if (match.exception_codes.includes("excluded_from_claim")) return "excluded";
  if (match.exception_codes.length > 0) return "review";
  return "eligible";
}

function primaryIssue(match: Match) {
  return issuePriority.find((code) => match.exception_codes.includes(code));
}

function nextExceptionLine(claim?: Claim) {
  return claim?.exceptions.find((item) => item.ledger_id)?.ledger_id;
}

function recommendationFor(match?: Match) {
  if (!match) return { title: "Select a claim line", detail: "Choose an exception to review its evidence." };
  const issue = primaryIssue(match);
  if (issue === "excluded_from_claim") {
    return { title: "Held out of this claim", detail: "This line is preserved in the ledger but excluded from reimbursement." };
  }
  if (issue === "duplicate_expense") {
    return { title: "Exclude confirmed duplicate", detail: "The same vendor, amount and invoice description already appear on GL-9006." };
  }
  if (issue === "period_of_performance") {
    return { title: "Move to the correct reporting period", detail: "This October payroll line should not be included in the September reimbursement claim." };
  }
  if (issue === "missing_receipt" || issue === "missing_payroll") {
    return { title: "Attach supporting evidence", detail: "This cost remains blocked until the finance manager links the required document." };
  }
  if (issue === "ineligible_participant") {
    return { title: "Exclude unless program purpose is documented", detail: "The description indicates a staff celebration; the source permits only a direct programmatic purpose included in the award." };
  }
  return { title: "Eligible — checks passed", detail: "No unresolved exception remains on this line." };
}

function resolutionFor(match?: Match) {
  const issue = match ? primaryIssue(match) : undefined;
  if (issue === "duplicate_expense") {
    return {
      action: "exclude" as const,
      label: "Exclude confirmed duplicate",
      reason: "Confirmed duplicate of GL-9006; hold this copy out of reimbursement.",
    };
  }
  if (issue === "period_of_performance") {
    return {
      action: "exclude" as const,
      label: "Move out of September claim",
      reason: "October payroll belongs to the next reporting period.",
    };
  }
  if (issue === "missing_receipt" || issue === "missing_payroll") {
    return {
      action: "attach_receipt" as const,
      label: "Link demo receipt record",
      reason: "Finance manager linked the demo receipt record to this claim line.",
    };
  }
  return null;
}

function reasonForState(response: DemoResponse) {
  const claim = response.claim;
  const flow = claim?.meta?.guided_flow;
  const phase = flow?.phase ?? response.phase;
  if (phase === "approved") {
    return flow?.manager_approval?.reason
      ?? "All line exceptions are resolved, evidence is linked and the approval boundary is proven.";
  }
  if (phase === "ai_approval_denied") {
    return "All line exceptions are resolved, evidence is linked and the approval boundary is proven.";
  }
  if (phase === "future_claim_held") return "Agent requests approval of its prepared package.";
  if (phase === "policy_active") {
    return "Submit a separate October staff-lunch claim to test the approved rule.";
  }
  if (phase === "policy_pending_approval") {
    return "The rule is narrow, evidence-backed and keeps a human review hold.";
  }
  if (phase === "ready_for_policy") {
    return "Turn this correction into a reusable, human-approved review rule.";
  }
  if (phase === "decision_recorded") {
    const nextLineId = nextExceptionLine(claim);
    const nextMatch = claim?.matches.find((match) => match.ledger_id === nextLineId);
    return resolutionFor(nextMatch)?.reason
      ?? "Resolve the next exception as a separate, audited action.";
  }
  return "Staff celebration with no direct programmatic purpose.";
}

class ClaimsApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.text();
    let detail = body;
    try { detail = JSON.parse(body).detail ?? body; } catch { /* Plain-text service error. */ }
    throw new ClaimsApiError(typeof detail === "string" ? detail : `Request failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
}

export function ClaimDemo() {
  const [demo, setDemo] = useState<DemoResponse | null>(null);
  const [mode, setMode] = useState<"loading" | "decision" | "complete" | "error">("loading");
  const [selectedId, setSelectedId] = useState("GL-9005");
  const [reason, setReason] = useState("Staff celebration with no direct programmatic purpose.");
  const [showClean, setShowClean] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [audit, setAudit] = useState<Array<{ id: string; action: string; allowed: boolean; reason?: string; at?: string }> | null>(null);

  const start = useCallback(async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const next = await readJson<DemoResponse>("/v1/claims/demo", {
        method: "POST",
        body: JSON.stringify({ phase: "start" }),
      });
      setDemo(next);
      setMode("decision");
      setSelectedId("GL-9005");
      setReason("Staff celebration with no direct programmatic purpose.");
      setShowClean(false);
      setAudit(null);
      if (next.claim_id) window.localStorage.setItem("swarmcfo-guided-claim", next.claim_id);
    } catch (err) {
      setMode("error");
      setError(err instanceof Error ? err.message : "Claims service is unavailable.");
    } finally {
      setBusy(false);
    }
  }, []);

  const bootstrap = useCallback(async () => {
    setMode("loading");
    try {
      const savedClaimId = window.localStorage.getItem("swarmcfo-guided-claim");
      if (savedClaimId) {
        try {
          const saved = await readJson<DemoResponse>(
            `/v1/claims/${encodeURIComponent(savedClaimId)}/guided`,
          );
          setDemo(saved);
          setMode(saved.phase === "approved" ? "complete" : "decision");
          setSelectedId(nextExceptionLine(saved.claim) ?? "GL-9005");
          setReason(reasonForState(saved));
          return;
        } catch (err) {
          if (!(err instanceof ClaimsApiError) || err.status !== 404) throw err;
          window.localStorage.removeItem("swarmcfo-guided-claim");
        }
      }
      const pending = await readJson<PendingResponse>("/v1/claims/pending");
      if (pending.active?.awaiting_manager && pending.active.claim) {
        setDemo({
          phase: "awaiting_manager",
          awaiting_manager: true,
          claim_id: pending.active.claim_id,
          question: pending.active.question,
          claim: pending.active.claim,
        });
        setMode("decision");
        setReason("Staff celebration with no direct programmatic purpose.");
        window.localStorage.setItem("swarmcfo-guided-claim", pending.active.claim_id);
        return;
      }
      await start();
    } catch (err) {
      setMode("error");
      setError(err instanceof Error ? err.message : "Claims service is unavailable. Your saved review is preserved.");
    }
  }, [start]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const claim = demo?.claim;
  const orderedMatches = useMemo(() => {
    const rows = [...(claim?.matches ?? [])];
    return rows.sort((a, b) => {
      const aRank = lineStatus(a) === "eligible" ? 1 : 0;
      const bRank = lineStatus(b) === "eligible" ? 1 : 0;
      return aRank - bRank || b.amount_cents - a.amount_cents;
    });
  }, [claim]);

  const selected =
    orderedMatches.find((match) => match.ledger_id === selectedId) ?? orderedMatches[0];
  const visibleMatches = orderedMatches.filter(
    (match) => showClean || lineStatus(match) !== "eligible" || match.ledger_id === selectedId,
  );
  const linkedEvidence = (claim?.evidence ?? []).filter(
    (item) => item.linked_ledger_id === selected?.ledger_id,
  );
  const source = claim?.meta?.rule_source;
  const providerReceipts = claim?.meta?.provider_receipts;
  const ruleRefresh = claim?.meta?.rule_refresh;
  const liveRuleForReview = ruleRefresh?.status === "needs_human" && !!providerReceipts?.claude?.exact_quote;
  const flow = claim?.meta?.guided_flow;
  const liveQuestionAnswered = liveRuleForReview && !!flow?.decision;
  const workflowPhase = flow?.phase ?? (demo?.awaiting_manager ? "awaiting_decision" : demo?.phase ?? "awaiting_decision");
  const phaseText = phaseCopy[workflowPhase] ?? phaseCopy.awaiting_decision;
  const futureClaim = demo?.future_claim;
  const futureLine = futureClaim?.matches?.find((match) =>
    match.exception_codes.includes("learned_policy_hold"),
  ) ?? futureClaim?.matches?.[0];
  const futureWorkItem = demo?.future_claim_work_item
    ?? demo?.workflow?.future_claim_work_item
    ?? demo?.work_item;
  const futureClaimId = futureClaim?.id ?? flow?.future_claim_id;
  const futureReportingPeriod = futureClaim?.reporting_period ?? flow?.future_claim_reporting_period;
  const futurePolicyId = flow?.future_claim_policy_id ?? flow?.policy_id;
  const futureMatchBasis = demo?.match_basis ?? flow?.future_claim_match_basis;
  const futureMatchLabel = typeof futureMatchBasis === "string"
    ? futureMatchBasis
    : futureMatchBasis?.matched_terms?.length
      ? futureMatchBasis.matched_terms.join(", ")
      : futureMatchBasis?.matcher;
  const futureWorkItemId = futureWorkItem?.id ?? flow?.future_claim_work_item_id;
  const futureWorkItemState = futureWorkItem?.state ?? (futureClaimId ? "HELD" : undefined);
  const resolutionTarget = flow?.decision?.decision === "keep" ? 4 : 3;
  const workspaceLabel =
    workflowPhase === "awaiting_decision"
      ? "Human decision"
      : workflowPhase === "decision_recorded"
        ? "Exception resolution"
        : workflowPhase === "ready_for_policy" || workflowPhase === "policy_pending_approval"
          ? "Learned guardrail"
          : workflowPhase === "approved"
            ? "Approval complete"
            : "Approval control";
  const activeStage =
    mode === "complete" || workflowPhase === "approved"
      ? 6
      : workflowPhase === "ai_approval_denied" || workflowPhase === "future_claim_held"
        ? 6
        : workflowPhase === "ready_for_policy" || workflowPhase === "policy_pending_approval" || workflowPhase === "policy_active"
          ? 5
          : 4;
  const eligible = claim?.totals?.eligible_cents ?? claim?.totals?.claimed_cents ?? 0;
  const excluded = claim?.totals?.excluded_cents ?? 0;
  const duplicateHold = claim?.totals?.duplicate_cents ?? 0;
  const heldOut = excluded + duplicateHold;
  const cleanCount = (claim?.matches ?? []).filter((match) => lineStatus(match) === "eligible").length;
  const recommendation = recommendationFor(selected);
  const resolution = resolutionFor(selected);
  const selectedException = claim?.exceptions.find(
    (item) => item.ledger_id === selected?.ledger_id,
  );
  const selectedResolution = flow?.resolved_exceptions?.find(
    (item) => item.ledger_id === selected?.ledger_id,
  );
  const selectedIssue = selected ? primaryIssue(selected) : undefined;
  const isGoverningRuleLine = selected?.ledger_id === "GL-9005";
  const timelineEvents = useMemo(() => {
    const events: Array<{ label: string; actor: string }> = [
      { label: "Claim prepared", actor: "Claims agent" },
      { label: "Exceptions surfaced", actor: "Deterministic checks" },
    ];
    if (flow?.decision) {
      events.push({ label: "Decision recorded", actor: "Finance manager" });
    } else {
      events.push({ label: "Decision requested", actor: "Claims agent" });
    }
    for (const item of flow?.resolved_exceptions ?? []) {
      events.push({ label: `${item.ledger_id ?? "Line"} resolved`, actor: "Finance manager" });
    }
    if (flow?.policy_id) events.push({ label: "Future rule proposed", actor: "Claims agent" });
    if (flow?.policy_status === "active") events.push({ label: "Future rule approved", actor: "Finance manager" });
    if (flow?.future_claim_id || futureClaim?.id) {
      events.push({ label: "Separate October claim held", actor: "Policy engine" });
    }
    if (flow?.ai_approval_receipt?.denied) events.push({ label: "Automated approval blocked", actor: "Policy engine" });
    if (flow?.manager_approval) events.push({ label: "Claim approved", actor: "Finance manager" });
    return events;
  }, [flow, futureClaim?.id]);

  async function runAction(
    action: () => Promise<DemoResponse>,
    successMessage: string,
    nextReason?: string,
  ) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const next = await action();
      setDemo((previous) => previous?.claim?.id === next.claim?.id ? { ...previous, ...next } : next);
      setMode(next.phase === "approved" ? "complete" : "decision");
      setNotice(successMessage);
      if (nextReason) setReason(nextReason);
      const nextLine = nextExceptionLine(next.claim);
      if (nextLine) setSelectedId(nextLine);
      else setSelectedId("GL-9005");
      return next;
    } catch (err) {
      setError(err instanceof Error ? err.message : "The workflow action failed.");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function decide(kind: "exclude" | "allow") {
    if (kind === "allow" && reason.trim() === "Staff celebration with no direct programmatic purpose.") {
      setReason("");
      setNotice("Explain the documented program purpose before allowing this expense. Supporting evidence will still be required.");
      document.getElementById("decision-reason")?.focus();
      return;
    }
    if (!claim || !reason.trim()) {
      setNotice("Add a short reason before recording the decision.");
      return;
    }
    const next = await runAction(
      () => readJson<DemoResponse>(`/v1/claims/${encodeURIComponent(claim.id)}/decisions`, {
        method: "POST",
        body: JSON.stringify({ decision: kind === "exclude" ? "exclude" : "keep", reason: reason.trim() }),
      }),
      "Decision recorded. Only the catering line changed; the other exceptions remain explicit.",
    );
    const nextLineId = nextExceptionLine(next?.claim);
    const nextMatch = next?.claim?.matches.find((match) => match.ledger_id === nextLineId);
    setReason(
      resolutionFor(nextMatch)?.reason
        ?? "Resolve the next exception as a separate, audited action.",
    );
  }

  async function resolveSelected() {
    if (!claim || !selected || !resolution || !reason.trim()) return;
    const suffix = claim.id.split("-").at(-1) ?? "claim";
    const next = await runAction(
      () => readJson<DemoResponse>(
        `/v1/claims/${encodeURIComponent(claim.id)}/exceptions/${encodeURIComponent(selected.ledger_id)}/resolve`,
        {
          method: "POST",
          body: JSON.stringify({
            action: resolution.action,
            reason: reason.trim(),
            ...(resolution.action === "attach_receipt"
              ? {
                  evidence_id: `ev-guided-${suffix}-${selected.ledger_id}`,
                  filename: selected.ledger_id === "GL-9005" ? "catering_program_lunch.pdf" : "staples_toner_0922.pdf",
                }
              : {}),
          }),
        },
      ),
      `${selected.ledger_id} resolved as a separate audited action.`,
    );
    const nextLineId = nextExceptionLine(next?.claim);
    const nextMatch = next?.claim?.matches.find((match) => match.ledger_id === nextLineId);
    setReason(
      resolutionFor(nextMatch)?.reason
        ?? "Turn this correction into a reusable, human-approved review rule.",
    );
  }

  async function proposeFutureRule() {
    if (!claim || !reason.trim()) return;
    await runAction(
      () => readJson<DemoResponse>(`/v1/claims/${encodeURIComponent(claim.id)}/policies`, {
        method: "POST",
        body: JSON.stringify({ reason: reason.trim() }),
      }),
      "Future rule proposed. It is not active until a manager approves it.",
      "The rule is narrow, evidence-backed and keeps a human review hold.",
    );
  }

  async function approveFutureRule() {
    const policyId = flow?.policy_id ?? demo?.policy?.id;
    if (!policyId || !reason.trim()) return;
    await runAction(
      () => readJson<DemoResponse>(`/v1/policies/${encodeURIComponent(policyId)}/approve`, {
        method: "POST",
        body: JSON.stringify({ reason: reason.trim() }),
      }),
      "Policy approved as a distinct manager action.",
      "Submit a separate October staff-lunch claim to test the approved rule.",
    );
  }

  async function submitNextPeriodClaim() {
    if (!claim || !reason.trim()) return;
    await runAction(
      () => readJson<DemoResponse>(
        `/v1/claims/${encodeURIComponent(claim.id)}/next-period-submissions`,
        {
          method: "POST",
          body: JSON.stringify({
            reason: reason.trim(),
            reporting_period: "2025-10",
            date: "2025-10-08",
            vendor: "Marina Cafe",
            description: "All-hands staff lunch — October",
            amount_cents: 86000,
            budget_line: "supplies",
            evidence_id: "ev-october-staff-lunch",
            filename: "october_staff_lunch.pdf",
          }),
        },
      ),
      "A separate October claim was held by the approved rule. The new claim and work item are shown in Decision proof.",
      "Agent requests approval of its prepared package.",
    );
  }

  async function testApprovalBoundary() {
    if (!claim || !reason.trim()) return;
    await runAction(
      () => readJson<DemoResponse>(`/v1/claims/${encodeURIComponent(claim.id)}/approval-attempts`, {
        method: "POST",
        body: JSON.stringify({ reason: reason.trim() }),
      }),
      "Automated approval denied by the role boundary and written to audit.",
      "All line exceptions are resolved, evidence is linked and the approval boundary is proven.",
    );
  }

  async function approveClaim() {
    if (!claim || !reason.trim()) return;
    await runAction(
      () => readJson<DemoResponse>(`/v1/claims/${encodeURIComponent(claim.id)}/approve`, {
        method: "POST",
        body: JSON.stringify({ reason: reason.trim() }),
      }),
      "Manager approved the corrected package. No automated actor received approval authority.",
    );
  }

  async function refreshRule() {
    if (!claim || busy) return;
    setBusy(true);
    setRefreshing(true);
    setError(null);
    setNotice(null);
    try {
      const result = await readJson<{ status: string }>(`/v1/claims/${encodeURIComponent(claim.id)}/rules/refresh`, {
        method: "POST", body: JSON.stringify({}),
      });
      const next = await readJson<DemoResponse>(`/v1/claims/${encodeURIComponent(claim.id)}/guided`);
      setDemo(next);
      setAudit(null);
      setNotice(result.status === "applied"
        ? "Official source refreshed. The cited interpretation and retrieval receipt are saved."
        : "The live interpretation needs your review. Read its proposed question and citation below before deciding.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live refresh failed. Review is required.");
      // Rehydrate the persisted failure receipt without discarding the manager's input.
      try { setDemo(await readJson<DemoResponse>(`/v1/claims/${encodeURIComponent(claim.id)}/guided`)); } catch { /* Preserve current review during an outage. */ }
    } finally { setRefreshing(false); setBusy(false); }
  }

  async function loadAudit() {
    if (!claim) return;
    try {
      const result = await readJson<{ events: NonNullable<typeof audit> }>(`/v1/claims/${encodeURIComponent(claim.id)}/audit`);
      setAudit(result.events);
    } catch (err) { setError(err instanceof Error ? err.message : "Audit receipts could not be loaded."); }
  }

  if (mode === "loading") {
    return (
      <main className={styles.shell}>
        <div className={styles.loadingCard}>
          <span className={styles.loader} />
          <strong>Preparing the claim review</strong>
          <p>Matching the ledger, evidence and award rules.</p>
        </div>
      </main>
    );
  }

  if (mode === "error" || !claim) {
    return (
      <main className={styles.shell}>
        <div className={styles.errorCard}>
          <span className={styles.eyebrow}>Demo service offline</span>
          <h1>Start the Claims API, then retry.</h1>
          <p>{error ?? "No claim package was returned."}</p>
          <button type="button" onClick={() => void bootstrap()} disabled={busy}>
            Retry connection
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.brandBlock}>
          <div className={styles.mark}>S</div>
          <div>
            <span className={styles.eyebrow}>SwarmCFO Claims</span>
            <h1>{claim.nonprofit}</h1>
          </div>
        </div>
        <div className={styles.claimMeta}>
          <div>
            <span>Award</span>
            <strong>{claim.award.award_id}</strong>
          </div>
          <div>
            <span>Reporting period</span>
            <strong>{claim.reporting_period}</strong>
          </div>
          <div>
            <span>Revision</span>
            <strong>{String(claim.meta?.revision ?? 1).padStart(2, "0")}</strong>
          </div>
          <span className={`${styles.statePill} ${workflowPhase === "approved" ? styles.ready : ""}`}>
            {phaseText.status}
          </span>
        </div>
      </header>

      <section className={styles.progress} aria-label="Claim workflow">
        {stages.map((stage, index) => {
          const number = index + 1;
          const done = number < activeStage || mode === "complete";
          const active = number === activeStage && mode !== "complete";
          return (
            <div
              className={`${styles.step} ${done ? styles.done : ""} ${active ? styles.active : ""}`}
              key={stage}
            >
              <span>{done ? "✓" : number}</span>
              <small>{stage}</small>
            </div>
          );
        })}
      </section>

      <section className={styles.metrics} aria-label="Claim totals">
        <div>
          <span>Original ledger</span>
          <strong>{money(claim.totals.gl_cents)}</strong>
          <small>9 source entries</small>
        </div>
        <div>
          <span>Eligible claim</span>
          <strong>{money(eligible)}</strong>
          <small>{phaseText.metric}</small>
        </div>
        <div>
          <span>Held out of claim</span>
          <strong>{money(heldOut)}</strong>
          <small>{duplicateHold ? "Includes unresolved duplicate hold" : "Not included in reimbursement"}</small>
        </div>
        <div>
          <span>Reconciliation gap</span>
          <strong className={styles.good}>{money(claim.totals.recon_gap_cents)}</strong>
          <small>Eligible + held = ledger</small>
        </div>
      </section>

      <section className={styles.workspace}>
        <aside className={styles.linePanel}>
          <div className={styles.panelHeading}>
            <div>
              <span className={styles.eyebrow}>Claim lines</span>
              <h2>Review exceptions</h2>
            </div>
            <span className={styles.count}>{claim.matches.length}</span>
          </div>
          <div className={styles.lineList}>
            {visibleMatches.map((match) => {
              const status = lineStatus(match);
              const mainIssue = primaryIssue(match);
              return (
                <button
                  className={`${styles.lineItem} ${selected?.ledger_id === match.ledger_id ? styles.selected : ""}`}
                  type="button"
                  key={match.ledger_id}
                  onClick={() => {
                    setSelectedId(match.ledger_id);
                    if (workflowPhase === "decision_recorded") {
                      const nextResolution = resolutionFor(match);
                      if (nextResolution) setReason(nextResolution.reason);
                    }
                  }}
                  disabled={busy}
                >
                  <span className={`${styles.statusDot} ${styles[status]}`} />
                  <span className={styles.lineCopy}>
                    <strong>{match.vendor}</strong>
                    <small>{(mainIssue ? statusCopy[mainIssue] : undefined) ?? (status === "eligible" ? "Checks passed" : "Review")}</small>
                  </span>
                  <span className={styles.amount}>{money(match.amount_cents)}</span>
                </button>
              );
            })}
          </div>
          <button className={styles.passedRow} type="button" onClick={() => setShowClean((value) => !value)}>
            <span>✓</span>
            <div>
              <strong>{cleanCount} lines passed</strong>
              <small>{showClean ? "Hide passed lines" : "Show passed lines"}</small>
            </div>
          </button>
        </aside>

        <section className={styles.decisionPanel}>
          {selected ? (
            <>
              <div className={styles.decisionTop}>
                <div>
                  <span className={styles.eyebrow}>{workspaceLabel}</span>
                  <h2>{selected.vendor}</h2>
                  <p>{selected.description}</p>
                </div>
                <strong className={styles.heroAmount}>{money(selected.amount_cents)}</strong>
              </div>

              {workflowPhase === "awaiting_decision" && (
                <div className={styles.questionCard}>
                  <span>Claims agent asks</span>
                  <p>{demo?.question ?? "Was this catering for participants or a staff-only celebration?"}</p>
                </div>
              )}

              <div className={`${styles.recommendation} ${lineStatus(selected) === "eligible" ? styles.recommendationOk : ""}`}>
                <span className={styles.warningIcon}>{lineStatus(selected) === "eligible" ? "✓" : "!"}</span>
                <div>
                  <span>Recommendation</span>
                  <strong>{recommendation.title}</strong>
                  <p>{recommendation.detail}</p>
                </div>
              </div>

              {demo?.policy?.rule && ["policy_pending_approval", "policy_active"].includes(workflowPhase) && (
                <div className={styles.questionCard}>
                  <span>{workflowPhase === "policy_pending_approval" ? "Proposed future rule · awaiting manager approval" : "Manager-approved future rule"}</span>
                  <p>{demo.policy.rule}</p>
                </div>
              )}

              <div className={styles.checkGrid}>
                <div>
                  <span className={styles.checkOk}>✓</span>
                  <p><strong>Ledger entry</strong><small>{selected.ledger_id} · {selected.date}</small></p>
                </div>
                <div>
                  <span className={linkedEvidence.length ? styles.checkOk : styles.checkWarn}>
                    {linkedEvidence.length ? "✓" : "!"}
                  </span>
                  <p><strong>Documentation</strong><small>{linkedEvidence.length ? `${linkedEvidence.length} file linked` : "No receipt linked"}</small></p>
                </div>
                <div>
                  <span className={selectedIssue ? styles.checkWarn : styles.checkOk}>{selectedIssue ? "!" : "✓"}</span>
                  <p>
                    <strong>{isGoverningRuleLine ? "Governing rule" : "Control check"}</strong>
                    <small>{selectedIssue ? statusCopy[selectedIssue] ?? "Review required" : "Checks passed"}</small>
                  </p>
                </div>
                <div>
                  <span className={styles.checkMuted}>—</span>
                  <p><strong>Payment evidence</strong><small>External match not connected</small></p>
                </div>
              </div>

              <div className={styles.reasonBlock}>
                <label htmlFor="decision-reason">{phaseText.reasonLabel} <span>Required</span></label>
                <textarea
                  id="decision-reason"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  disabled={busy || workflowPhase === "approved"}
                  rows={2}
                />
                <small>{phaseText.reasonHelp}</small>
              </div>

              {notice && <p className={styles.notice} role="status">{notice}</p>}
              {error && <p className={styles.inlineError} role="alert">{error}</p>}

              <div className={styles.decisionActions}>
                {workflowPhase === "approved" ? (
                  <button className={styles.primaryButton} type="button" onClick={() => void start()} disabled={busy}>
                    Review a fresh claim
                  </button>
                ) : workflowPhase === "awaiting_decision" ? (
                  <>
                    <button className={styles.primaryButton} type="button" onClick={() => void decide("exclude")} disabled={busy || !reason.trim()}>
                      {busy ? "Recording…" : "Exclude from claim"}
                    </button>
                    <button className={styles.secondaryButton} type="button" onClick={() => void decide("allow")} disabled={busy || !reason.trim()}>
                      Allow with documented exception
                    </button>
                  </>
                ) : workflowPhase === "decision_recorded" && resolution ? (
                  <button className={styles.primaryButton} type="button" onClick={() => void resolveSelected()} disabled={busy || !reason.trim()}>
                    {busy ? "Recording…" : resolution.label}
                  </button>
                ) : workflowPhase === "decision_recorded" ? (
                  <p className={styles.actionHint}>Select one of the remaining amber exceptions to continue.</p>
                ) : workflowPhase === "ready_for_policy" ? (
                  <button className={styles.primaryButton} type="button" onClick={() => void proposeFutureRule()} disabled={busy || !reason.trim()}>
                    {busy ? "Proposing…" : "Propose future rule"}
                  </button>
                ) : workflowPhase === "policy_pending_approval" ? (
                  <button className={styles.primaryButton} type="button" onClick={() => void approveFutureRule()} disabled={busy || !reason.trim()}>
                    {busy ? "Approving…" : "Approve future rule"}
                  </button>
                ) : workflowPhase === "policy_active" ? (
                  <button className={styles.primaryButton} type="button" onClick={() => void submitNextPeriodClaim()} disabled={busy || !reason.trim()}>
                    {busy ? "Submitting…" : "Submit independent October claim"}
                  </button>
                ) : workflowPhase === "future_claim_held" ? (
                  <button className={styles.primaryButton} type="button" onClick={() => void testApprovalBoundary()} disabled={busy || !reason.trim()}>
                    {busy ? "Testing…" : "Test automated approval"}
                  </button>
                ) : workflowPhase === "ai_approval_denied" ? (
                  <button className={styles.primaryButton} type="button" onClick={() => void approveClaim()} disabled={busy || !reason.trim()}>
                    {busy ? "Approving…" : "Approve corrected claim"}
                  </button>
                ) : (
                  <p className={styles.actionHint}>This workflow state is read-only.</p>
                )}
              </div>
            </>
          ) : (
            <p>No claim line selected.</p>
          )}
        </section>

        <aside className={styles.proofPanel}>
          <div className={styles.panelHeading}>
            <div>
              <span className={styles.eyebrow}>Decision proof</span>
              <h2>{workflowPhase === "approved" ? "Approval and evidence" : selectedIssue ? "Why this is held" : "Decision evidence"}</h2>
            </div>
          </div>

          <div className={styles.proofCard}>
            <div className={styles.proofTitle}>
              <span className={styles.sourceIcon}>§</span>
              <div>
                <strong>{isGoverningRuleLine ? "Governing rule" : selectedResolution ? "Recorded resolution" : "Deterministic claim control"}</strong>
                <small>
                  {isGoverningRuleLine
                    ? liveRuleForReview ? liveQuestionAnswered ? "Live official excerpt · manager response recorded" : "Live official excerpt · interpretation needs review" : source?.provenance ?? "Authoritative source excerpt"
                    : selectedResolution
                      ? "Audited manager action"
                      : "Checked against ledger and reporting rules"}
                </small>
              </div>
            </div>
            <blockquote>
              “{isGoverningRuleLine
                ? liveRuleForReview ? providerReceipts?.claude?.exact_quote : source?.quote ?? "Entertainment costs are unallowable unless they have a specific and direct programmatic purpose and are included in the Federal award."
                : selectedResolution?.reason ?? selectedException?.message ?? recommendation.detail}”
            </blockquote>
            {isGoverningRuleLine && source?.url ? (
              <a href={liveRuleForReview ? providerReceipts?.apify?.source_url : source.url} target="_blank" rel="noreferrer">
                {source.title ?? "Open source"} ↗
              </a>
            ) : null}
            <span className={isGoverningRuleLine && (source?.live_refresh || liveQuestionAnswered) ? styles.liveBadge : styles.fixtureBadge}>
              {isGoverningRuleLine
                ? source?.live_refresh
                  ? "Live source refreshed"
                  : liveRuleForReview ? liveQuestionAnswered ? "Live source · manager response recorded" : "Live source · human review required" : "Authoritative snapshot · live refresh pending"
                : selectedResolution
                  ? "Resolution preserved"
                  : "Code-enforced check"}
            </span>
            {isGoverningRuleLine && workflowPhase === "awaiting_decision" && (
              <div className={styles.sourceActions}>
                <button className={styles.secondaryButton} type="button" onClick={() => void refreshRule()} disabled={busy}>
                  {refreshing ? "Refreshing official rule…" : "Refresh official rule"}
                </button>
                <p className={styles.truthLine}>{liveRuleForReview ? "The retrieved quote is verified. The manager still decides whether this expense belongs in the claim." : "The bundled excerpt remains labeled until a live retrieval and verified interpretation succeed."}</p>
              </div>
            )}
            {isGoverningRuleLine && ruleRefresh?.status && ruleRefresh.status !== "applied" && !liveQuestionAnswered && (
              <p className={styles.notice} role="status">
                {ruleRefresh.status === "needs_human"
                  ? ruleRefresh.suggested_question || "The live interpretation needs human review."
                  : "Live refresh did not complete. Review the bundled source manually; no live result has been applied."}
              </p>
            )}
            {isGoverningRuleLine && providerReceipts?.claude?.exact_quote && !source?.live_refresh && (
              <details className={styles.technical}>
                <summary>{liveQuestionAnswered ? "Live interpretation and manager response" : "Live interpretation awaiting review"}</summary>
                <p>{providerReceipts.claude.rule}</p>
                <blockquote>“{providerReceipts.claude.exact_quote}”</blockquote>
                {liveQuestionAnswered && <p>Manager response: {flow?.decision?.reason}</p>}
              </details>
            )}
          </div>

          <div className={styles.proofCard}>
            <div className={styles.proofTitle}>
              <span className={styles.ledgerIcon}>↔</span>
              <div>
                <strong>Evidence match</strong>
                <small>Ledger, document and payment context</small>
              </div>
            </div>
            <dl>
              <div><dt>Ledger confidence</dt><dd>{Math.round((selected?.confidence ?? 0) * 100)}%</dd></div>
              <div><dt>Documents</dt><dd>{linkedEvidence.length || "None"}</dd></div>
              <div><dt>Payment match</dt><dd className={styles.pendingText}>Not connected</dd></div>
            </dl>
            <p className={styles.truthLine}>Payment verification is pending; reimbursement eligibility is a separate question.</p>
          </div>

          {futureClaimId && (
            <div className={`${styles.proofCard} ${styles.futureClaimCard}`}>
              <div className={styles.proofTitle}>
                <span className={styles.holdIcon}>Ⅱ</span>
                <div>
                  <strong>Independent October claim held</strong>
                  <small>Approved rule applied to a new package</small>
                </div>
              </div>
              <dl>
                <div>
                  <dt>New claim</dt>
                  <dd className={styles.receiptValue}>{futureClaimId}</dd>
                </div>
                <div><dt>Reporting period</dt><dd>{futureReportingPeriod ?? "2025-10"}</dd></div>
                <div>
                  <dt>New claim line</dt>
                  <dd className={styles.receiptValue}>
                    {futureLine
                      ? `${futureLine.ledger_id} · ${futureLine.vendor} · ${money(futureLine.amount_cents)}`
                      : "October staff lunch · $860"}
                  </dd>
                </div>
                <div>
                  <dt>Active policy</dt>
                  <dd className={styles.receiptValue}>
                    {futurePolicyId ?? "Approved policy"}
                    {flow?.future_claim_policy_version ? ` · v${flow.future_claim_policy_version}` : ""}
                  </dd>
                </div>
                <div>
                  <dt>HELD work item</dt>
                  <dd className={styles.receiptValue}>
                    {futureWorkItemId ?? "Recorded"} · <span className={styles.heldText}>{futureWorkItemState}</span>
                  </dd>
                </div>
              </dl>
              <p className={styles.truthLine}>
                This is not the corrected September line. It is a distinct claim, reporting period and work item.
                {futureMatchLabel ? ` Match: ${futureMatchLabel}.` : ""}
              </p>
            </div>
          )}

          {flow?.decision && (
            <div className={styles.proofCard}>
              <div className={styles.proofTitle}>
                <span className={styles.ledgerIcon}>◎</span>
                <div>
                  <strong>Governance checkpoint</strong>
                  <small>Decision, policy and approval stay separate</small>
                </div>
              </div>
              <dl>
                <div><dt>Manager decision</dt><dd>{flow.decision.decision === "exclude" ? "Exclude" : "Keep with evidence"}</dd></div>
                <div><dt>Line resolutions</dt><dd>{flow.resolved_exceptions?.length ?? 0} / {resolutionTarget}</dd></div>
                <div><dt>Future rule</dt><dd>{flow.policy_status === "active" ? "Approved" : flow.policy_id ? "Pending" : "Not proposed"}</dd></div>
                <div><dt>AI approval</dt><dd className={flow.ai_approval_receipt?.denied ? styles.deniedText : styles.pendingText}>{flow.ai_approval_receipt?.denied ? "Denied by code" : "Not attempted"}</dd></div>
              </dl>
            </div>
          )}

          {workflowPhase === "approved" && (
            <div className={`${styles.proofCard} ${styles.successCard}`}>
              <div className={styles.proofTitle}>
                <span className={styles.successIcon}>✓</span>
                <div>
                  <strong>Approval boundary proven</strong>
                  <small>Automated approval denied by code</small>
                </div>
              </div>
              <p>The corrected package was approved by the finance manager with zero unauthorized approvals.</p>
            </div>
          )}

          <details className={styles.technical}>
            <summary>Technical receipts</summary>
            <ul>
              <li>
                Rule retrieval:{" "}
                {source?.live_refresh || liveRuleForReview
                  ? `live · run ${source?.apify_run_id ?? providerReceipts?.apify?.run_id ?? "recorded"}`
                  : ruleRefresh?.status
                    ? `attempted · ${ruleRefresh.status}`
                    : "bundled authoritative excerpt"}
              </li>
              <li>
                Rule interpretation:{" "}
                {providerReceipts?.claude?.error
                  ? `held · ${providerReceipts.claude.error}`
                  : providerReceipts?.claude?.confidence != null
                    ? `${providerReceipts.claude.model ?? "Claude"} · confidence ${providerReceipts.claude.confidence}`
                    : "pending live refresh"}
              </li>
              <li>Payment API: not connected</li>
              <li>Receipt attachment: metadata-only demo fixture</li>
              <li>Decision math: deterministic code</li>
              <li>Learned-rule test: {futureClaimId ? "separate October claim held" : "not yet run"}</li>
              <li>Approval enforcement: role matrix in code</li>
            </ul>
            <button className={styles.secondaryButton} type="button" onClick={() => void loadAudit()}>Load audit receipts</button>
            {audit && <ol className={styles.auditList}>{audit.map((event) => (
              <li key={event.id}>
                <strong>{event.action} · {event.allowed ? "Recorded" : "Denied / review"}</strong>
                <p>{event.reason}</p>
                <small>{event.id} · {event.at}</small>
              </li>
            ))}</ol>}
          </details>
        </aside>
      </section>

      <section className={styles.timeline}>
        <div>
          <span className={styles.eyebrow}>Workflow timeline</span>
          <strong>{workflowPhase === "approved" ? "Actions in this demo run recorded" : phaseText.status}</strong>
        </div>
        <div className={styles.timelineSteps}>
          {timelineEvents.map((item, index) => (
            <div key={`${item.label}-${index}`}>
              <span>{index + 1}</span>
              <p><strong>{item.label}</strong><small>{item.actor}</small></p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
