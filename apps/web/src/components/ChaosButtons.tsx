"use client";

import { useState } from "react";
import Link from "next/link";
import { useWorld } from "@/hooks/useWorld";
import { refresh, resetDemo } from "@/lib/demo-store";
import { ClaimsRiskViz, type RiskVizData } from "@/components/suite/ClaimsRiskViz";
import {
  ClaimsLearningViz,
  type AuditRow,
  type LearningResults,
  type LearningStoryStep,
} from "@/components/suite/ClaimsLearningViz";

const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

export function ChaosButtons() {
  const { ready, error } = useWorld();
  const [note, setNote] = useState<string | null>(null);
  const [viz, setViz] = useState<RiskVizData | null>(null);
  const [story, setStory] = useState<LearningStoryStep[]>([]);
  const [results, setResults] = useState<LearningResults | null>(null);
  const [checks, setChecks] = useState<Record<string, boolean> | undefined>();
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [revisionDiff, setRevisionDiff] = useState<{
    from?: Record<string, unknown>;
    to?: Record<string, unknown>;
  } | null>(null);
  const [outcome, setOutcome] = useState("");
  const [features, setFeatures] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function runClaimsLearningLoop() {
    setBusy(true);
    setNote("Claims Agent preparing rev1 → ask → manager no…");
    try {
      const res = await fetch(`${API}/v1/claims/demo`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setStory(json.story || []);
      setResults(json.results || null);
      setChecks(json.checks);
      setAudit(json.audit || []);
      setRevisionDiff(json.revision_diff || null);
      setOutcome(json.outcome || "");
      if (json.viz) setViz(json.viz);
      setFeatures(json.answer_key?.features || json.answer_key?.hyphenate_loop || []);
      setNote(
        `Learning loop ${json.ok ? "PASS" : "partial"} · ${json.score}/100 · ${json.outcome || ""}`,
      );
      await refresh();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "claims learning loop failed");
    } finally {
      setBusy(false);
    }
  }

  async function runMissionDemo() {
    setNote("Running mission…");
    try {
      const res = await fetch(`${API}/v1/missions/demo`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      const ledger = json.job_ledger || {};
      setNote(
        `Mission ${json.ok ? "OK" : "partial"} · score ${json.score}/100 · spend $${((ledger.spent_cents || 0) / 100).toFixed(2)}`,
      );
    } catch (e) {
      setNote(e instanceof Error ? e.message : "mission demo failed");
    }
  }

  return (
    <section className="chaos">
      <h2>SwarmCFO Claims — learns, improves, proves</h2>
      <p className="sub">
        Governed Claims Agent + Finance Manager. Manager <em>no</em> becomes precedent and policy.
        Agent approve is denied in code.{" "}
        {error ? `API: ${error}` : ready ? "Connected." : "Connecting…"}{" "}
        <Link href="/suite/claims">Claims suite</Link>
      </p>
      <div className="grid">
        <button
          type="button"
          className="primary"
          disabled={busy}
          onClick={() => void runClaimsLearningLoop()}
        >
          <span className="label">{busy ? "Running learning loop…" : "Run Claims learning loop"}</span>
          <span className="detail">
            Ask $860 → manager no → rev2 → precedent → policy → next hold → DENIED agent → FM approve
          </span>
        </button>
        <button type="button" className="secondary" onClick={() => void runMissionDemo()}>
          <span className="label">Mission Margin (secondary)</span>
          <span className="detail">Budgeted AI job ledger — not the lead demo</span>
        </button>
        <button type="button" className="reset" onClick={() => void resetDemo()}>
          Reset
        </button>
      </div>
      {note && <p className="note">{note}</p>}

      {features.length > 0 && (
        <ul className="features">
          {features.slice(0, 8).map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      )}

      {(story.length > 0 || results) && (
        <div className="viz-slot">
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
        <div className="viz-slot">
          <ClaimsRiskViz data={viz} compact />
        </div>
      )}

      <style jsx>{`
        .chaos {
          padding: 0 2rem 1.25rem;
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.25rem;
          margin: 0 0 0.25rem;
        }
        .sub {
          margin: 0 0 1rem;
          color: var(--ink-muted);
          font-size: 0.9rem;
        }
        .sub :global(a) {
          color: var(--accent-bright);
        }
        .grid {
          display: flex;
          flex-wrap: wrap;
          gap: 0.65rem;
          align-items: center;
        }
        .primary,
        .secondary {
          text-align: left;
          background: #1f3328;
          border: 1px solid var(--accent);
          border-radius: 10px;
          padding: 1rem 1.15rem;
          color: var(--ink);
          max-width: 32rem;
          cursor: pointer;
        }
        .primary:disabled {
          opacity: 0.65;
          cursor: wait;
        }
        .secondary {
          border-color: #3d5a4a;
          background: #152018;
          max-width: 18rem;
        }
        .label {
          display: block;
          font-weight: 600;
          margin-bottom: 0.3rem;
        }
        .detail {
          font-size: 0.8rem;
          color: var(--ink-muted);
        }
        .note {
          margin: 0.75rem 0 0;
          font-size: 0.85rem;
          color: #9fd0ff;
        }
        .features {
          list-style: none;
          margin: 0.85rem 0 0;
          padding: 0;
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
        }
        .features li {
          font-size: 0.72rem;
          padding: 0.3rem 0.55rem;
          border-radius: 6px;
          border: 1px solid rgba(95, 212, 154, 0.35);
          background: rgba(61, 155, 106, 0.12);
          color: #c8e6d4;
        }
        .viz-slot {
          margin-top: 1rem;
          padding: 1rem;
          border-radius: 14px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(8, 12, 11, 0.55);
        }
        .reset {
          background: transparent;
          border: 1px dashed var(--line);
          color: var(--ink-muted);
          padding: 0.55rem 0.85rem;
          border-radius: 6px;
          font-size: 0.8rem;
          cursor: pointer;
        }
      `}</style>
    </section>
  );
}
