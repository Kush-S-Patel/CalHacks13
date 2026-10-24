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

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/v1/claims`, { cache: "no-store" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setList(json.claims || []);
      setErr(null);
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

  async function runDemo() {
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch(`${API}/v1/claims/demo`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setDemoScore(json.score ?? null);
      setStory((json.story as LearningStoryStep[]) || []);
      setResults((json.results as LearningResults) || null);
      setChecks(json.checks);
      setAudit((json.audit as AuditRow[]) || []);
      setRevisionDiff(json.revision_diff || json.claim?.meta?.revision_diff || null);
      setOutcome(json.outcome || "");
      if (json.viz) setViz(json.viz as RiskVizData);
      await load();
      if (json.claim?.id) await openClaim(json.claim.id);
      if (json.viz) setViz(json.viz as RiskVizData);
      if (json.story) setStory(json.story);
      if (json.results) setResults(json.results);
      if (json.audit) setAudit(json.audit);
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
        <button type="button" disabled={busy} onClick={() => void runDemo()}>
          {busy ? "Running learning loop…" : "Run Claims learning loop"}
        </button>
      </header>

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
        header button:disabled {
          opacity: 0.6;
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
