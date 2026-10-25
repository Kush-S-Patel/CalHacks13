"use client";

import { useCallback, useEffect, useState } from "react";
import { ClaimsRiskViz, type RiskVizData } from "./ClaimsRiskViz";
import {
  ClaimsLearningViz,
  type AuditRow,
  type LearningResults,
  type LearningStoryStep,
} from "./ClaimsLearningViz";

const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

type ClaimSummary = {
  id: string;
  nonprofit: string;
  award_id: string;
  period: string;
  status: string;
  risk_score: number | null;
  risk_band: string | null;
  claimed_cents: number;
  exception_count: number;
};

type ClaimDetail = {
  id: string;
  nonprofit: string;
  status: string;
  reporting_period: string;
  schedules_md: string;
  exceptions: { code?: string; message?: string }[];
  risk: RiskVizData & { corpus_priors?: Record<string, unknown>; drivers?: RiskVizData["drivers"] } | null;
  totals: Record<string, number>;
  award: { award_id: string; cfda: string; funder: string };
  meta?: Record<string, unknown>;
  log?: string[];
};

function usd(cents: number) {
  return `$${(cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function ClaimsPanel() {
  const [list, setList] = useState<ClaimSummary[]>([]);
  const [selected, setSelected] = useState<ClaimDetail | null>(null);
  const [viz, setViz] = useState<RiskVizData | null>(null);
  const [story, setStory] = useState<LearningStoryStep[]>([]);
  const [results, setResults] = useState<LearningResults | null>(null);
  const [checks, setChecks] = useState<Record<string, boolean> | undefined>();
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [revisionDiff, setRevisionDiff] = useState<{
    from?: Record<string, unknown>;
    to?: Record<string, unknown>;
  } | null>(null);
  const [outcome, setOutcome] = useState<string>("");
  const [demoScore, setDemoScore] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [pending, setPending] = useState<{
    claimId: string;
    question: string;
    who: string;
    about: string;
  } | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/v1/claims`, { cache: "no-store" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setList(json.claims || []);
      setErr(null);
      const pend = await fetch(`${API}/v1/claims/pending`, { cache: "no-store" });
      if (pend.ok) {
        const pjson = await pend.json();
        const active = pjson.active;
        if (active?.awaiting_manager) {
          setPending({
            claimId: active.claim_id,
            question: active.question || "",
            who: "Priya Shah · Finance Manager · Meridian Bookkeeping",
            about: "North Bay Catering · $860.00",
          });
        }
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "claims offline");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function openClaim(id: string) {
    const res = await fetch(`${API}/v1/claims/${encodeURIComponent(id)}`, { cache: "no-store" });
    if (!res.ok) {
      setErr(await res.text());
      return;
    }
    const json = await res.json();
    const claim = json.claim as ClaimDetail;
    setSelected(claim);
    if (claim.risk) {
      setViz({
        score: claim.risk.score,
        band: claim.risk.band,
        recommendation: claim.risk.recommendation,
        drivers: claim.risk.drivers,
        exceptions: claim.exceptions,
        corpus: claim.risk.corpus_priors,
        nonprofit: claim.nonprofit,
        claimed_cents: claim.totals?.eligible_cents ?? claim.totals?.claimed_cents,
      });
    }
    if (claim.meta?.revision_diff) {
      setRevisionDiff(claim.meta.revision_diff as { from?: Record<string, unknown>; to?: Record<string, unknown> });
    }
  }

  function applyDemo(json: Record<string, unknown>) {
    setDemoScore((json.score as number) ?? null);
    setStory((json.story as LearningStoryStep[]) || []);
    setResults((json.results as LearningResults) || null);
    setChecks(json.checks as Record<string, boolean> | undefined);
    setAudit((json.audit as AuditRow[]) || []);
    setRevisionDiff(
      (json.revision_diff as { from?: Record<string, unknown>; to?: Record<string, unknown> }) ||
        null,
    );
    setOutcome((json.outcome as string) || "");
    if (json.viz) setViz(json.viz as RiskVizData);
  }

  async function startInteractive() {
    setBusy(true);
    setErr(null);
    setPending(null);
    try {
      const res = await fetch(`${API}/v1/claims/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phase: "start" }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      applyDemo(json);
      const prompt = (json.manager_prompt || {}) as { who?: string; about?: string };
      setPending({
        claimId: json.claim_id,
        question: json.question || "",
        who: prompt.who || "Priya Shah · Finance Manager",
        about: prompt.about || "$860 catering",
      });
      await load();
      if (json.claim?.id) await openClaim(json.claim.id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "demo failed");
    } finally {
      setBusy(false);
    }
  }

  async function answerPriya(answer: string) {
    if (!pending) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch(`${API}/v1/claims/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phase: "resume", claim_id: pending.claimId, answer }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      applyDemo(json);
      if (json.awaiting_manager) {
        setPending({
          ...pending,
          question: json.question || pending.question,
        });
      } else {
        setPending(null);
      }
      await load();
      if (json.claim?.id) await openClaim(json.claim.id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "resume failed");
    } finally {
      setBusy(false);
    }
  }

  async function runDemo() {
    setBusy(true);
    setErr(null);
    setPending(null);
    try {
      const res = await fetch(`${API}/v1/claims/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phase: "full" }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      applyDemo(json);
      await load();
      if (json.claim?.id) await openClaim(json.claim.id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "demo failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="claims">
      <header>
        <div>
          <h1>SwarmCFO Claims</h1>
          <p>
            One deep corner: manager <em>no</em> → revision → precedent → policy → next-case hold →
            agent approve <strong>DENIED</strong> → finance manager approve. Append-only audit. Does
            not submit to the funder or alter the ledger.
          </p>
        </div>
        <div className="actions">
          <button type="button" disabled={busy} onClick={() => void startInteractive()}>
            {busy && !pending ? "Jordan working…" : "Start — pause for Priya"}
          </button>
          <button type="button" className="ghost" disabled={busy} onClick={() => void runDemo()}>
            Full loop
          </button>
        </div>
      </header>

      {pending && (
        <div className="priya">
          <p className="who">{pending.who}</p>
          <p className="about">{pending.about}</p>
          <p className="q">{pending.question}</p>
          <button
            type="button"
            disabled={busy}
            onClick={() => void answerPriya("No — that was our staff celebration. Exclude it.")}
          >
            No — staff celebration. Exclude it.
          </button>
        </div>
      )}

      {demoScore != null && (
        <p className="score">
          Learning-loop checks {demoScore}/100
          {results?.agent_approve_denied ? " · agent approve DENIED" : ""}
        </p>
      )}
      {err && <p className="err">{err}</p>}

      {(story.length > 0 || results) && (
        <div className="block">
          <ClaimsLearningViz
            story={story}
            results={results}
            checks={checks}
            audit={audit}
            revisionDiff={revisionDiff}
            outcome={outcome}
          />
        </div>
      )}

      {viz && (
        <div className="block">
          <h2 className="sec">Rejection risk (after revision)</h2>
          <ClaimsRiskViz data={viz} />
        </div>
      )}

      <div className="layout">
        <ul className="list">
          {list.length === 0 && <li className="empty">No claims yet — run the learning loop.</li>}
          {list.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={selected?.id === c.id ? "on" : ""}
                onClick={() => void openClaim(c.id)}
              >
                <strong>{c.nonprofit}</strong>
                <span>
                  {c.period} · {c.status} · risk {c.risk_score ?? "—"} ({c.risk_band ?? "—"}) ·{" "}
                  {usd(c.claimed_cents || 0)}
                </span>
              </button>
            </li>
          ))}
        </ul>

        <div className="detail">
          {!selected && <p className="empty">Select a claim for package schedules.</p>}
          {selected && (
            <>
              <h2>{selected.nonprofit}</h2>
              <p className="meta">
                {selected.award?.award_id} · {selected.reporting_period} · rev{" "}
                {String(selected.meta?.revision ?? "—")} · {selected.status}
              </p>
              {(selected.log || []).length > 0 && (
                <>
                  <h3>Agent log</h3>
                  <ul className="ex">
                    {selected.log!.slice(-8).map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                </>
              )}
              <h3>Package</h3>
              <pre className="md">{selected.schedules_md}</pre>
            </>
          )}
        </div>
      </div>

      <style jsx>{`
        .claims {
          padding: 1.5rem 2rem 3rem;
          max-width: 1180px;
        }
        header {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-start;
        }
        h1 {
          font-family: var(--font-display);
          font-size: 1.75rem;
          margin: 0 0 0.35rem;
        }
        header p {
          color: var(--ink-muted);
          max-width: 40rem;
          margin: 0;
          font-size: 0.92rem;
        }
        .actions {
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
        }
        header button {
          background: #1f4d3a;
          color: #e8f2ec;
          border: 0;
          border-radius: 8px;
          padding: 0.7rem 1.05rem;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
        }
        header button.ghost {
          background: transparent;
          border: 1px solid var(--line);
          color: var(--ink-muted);
          font-weight: 500;
        }
        header button:disabled {
          opacity: 0.6;
        }
        .priya {
          margin: 1rem 0;
          padding: 1rem 1.15rem;
          border-radius: 12px;
          border: 1px solid rgba(212, 180, 95, 0.45);
          background: rgba(80, 60, 20, 0.25);
          max-width: 40rem;
        }
        .priya .who {
          margin: 0;
          font-weight: 700;
        }
        .priya .about {
          margin: 0.2rem 0 0.5rem;
          color: var(--ink-muted);
          font-size: 0.8rem;
        }
        .priya .q {
          margin: 0 0 0.75rem;
          font-size: 0.9rem;
          line-height: 1.4;
        }
        .priya button {
          background: #1f4d3a;
          color: #e8f2ec;
          border: 0;
          border-radius: 8px;
          padding: 0.65rem 1rem;
          font-weight: 600;
          cursor: pointer;
        }
        .score {
          color: #7eb892;
          font-weight: 600;
        }
        .err {
          color: var(--warn);
        }
        .block {
          margin: 1rem 0 1.25rem;
        }
        .sec {
          font-family: var(--font-display);
          font-size: 1.05rem;
          margin: 0 0 0.65rem;
        }
        .layout {
          display: grid;
          grid-template-columns: minmax(220px, 300px) 1fr;
          gap: 1.25rem;
        }
        @media (max-width: 800px) {
          .layout {
            grid-template-columns: 1fr;
          }
        }
        .list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }
        .list button {
          width: 100%;
          text-align: left;
          background: transparent;
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 0.75rem 0.9rem;
          color: var(--ink);
          cursor: pointer;
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }
        .list button.on,
        .list button:hover {
          background: #1a2a22;
          border-color: #3d5c4a;
        }
        .list span {
          color: var(--ink-muted);
          font-size: 0.78rem;
        }
        .detail {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 1.25rem 1.4rem;
          background: rgba(12, 18, 16, 0.4);
        }
        .meta {
          color: var(--ink-muted);
          font-size: 0.82rem;
        }
        h3 {
          font-size: 0.8rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--ink-muted);
        }
        .ex {
          list-style: none;
          padding: 0;
          margin: 0 0 1rem;
          font-size: 0.82rem;
        }
        .ex li {
          padding: 0.25rem 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .md {
          white-space: pre-wrap;
          font-size: 0.75rem;
          line-height: 1.45;
          max-height: 420px;
          overflow: auto;
          background: #0a100e;
          border-radius: 8px;
          padding: 0.85rem;
          border: 1px solid var(--line);
        }
        .empty {
          color: var(--ink-muted);
        }
      `}</style>
    </section>
  );
}
