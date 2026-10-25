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

const EXCLUDE_ANSWER = "No — that was our staff celebration. Exclude it.";

export function ChaosButtons() {
  const { ready, error } = useWorld();
  const [note, setNote] = useState<string | null>(null);
  const [talk, setTalk] = useState<string>("");
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
  const [pending, setPending] = useState<{
    claimId: string;
    question: string;
    who: string;
    about: string;
  } | null>(null);
  const [hyphenate, setHyphenate] = useState<{
    score?: number;
    judging?: Record<string, boolean>;
  } | null>(null);

  function applyPayload(json: Record<string, unknown>) {
    setStory((json.story as LearningStoryStep[]) || []);
    setResults((json.results as LearningResults) || null);
    setChecks(json.checks as Record<string, boolean> | undefined);
    setAudit((json.audit as AuditRow[]) || []);
    setRevisionDiff(
      (json.revision_diff as { from?: Record<string, unknown>; to?: Record<string, unknown> }) || null,
    );
    setOutcome((json.outcome as string) || "");
    setTalk((json.talk_track as string) || "");
    if (json.viz) setViz(json.viz as RiskVizData);
    const ak = json.answer_key as { features?: string[]; hyphenate_loop?: string[] } | undefined;
    setFeatures(ak?.features || ak?.hyphenate_loop || []);
    if (json.hyphenate) {
      const h = json.hyphenate as { hyphenate_score?: number; judging?: Record<string, boolean> };
      setHyphenate({ score: h.hyphenate_score, judging: h.judging });
    }
  }

  async function startInteractive() {
    setBusy(true);
    setPending(null);
    setResults(null);
    setNote("Jordan is matching September’s GL…");
    try {
      const res = await fetch(`${API}/v1/claims/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phase: "start" }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      applyPayload(json);
      const prompt = json.manager_prompt || {};
      setPending({
        claimId: json.claim_id,
        question: json.question || "",
        who: prompt.who || "Priya Shah · Finance Manager",
        about: prompt.about || "$860 catering",
      });
      setNote("Jordan paused — Priya needs to answer before the package moves.");
      await refresh();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "could not start demo");
    } finally {
      setBusy(false);
    }
  }

  async function answerAsPriya(answer: string) {
    if (!pending) return;
    setBusy(true);
    setNote("Priya answering…");
    try {
      const res = await fetch(`${API}/v1/claims/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phase: "resume",
          claim_id: pending.claimId,
          answer,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      applyPayload(json);
      setPending(null);
      setNote(
        json.ok
          ? `Done · ${json.score}/100 · ${json.outcome || ""}`
          : `Partial · ${json.talk_track || json.hint || ""}`,
      );
      await refresh();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "resume failed");
    } finally {
      setBusy(false);
    }
  }

  async function runFullFast() {
    setBusy(true);
    setPending(null);
    setNote("Running full loop (auto-answer for checks)…");
    try {
      const res = await fetch(`${API}/v1/claims/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phase: "full" }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      applyPayload(json);
      setNote(`Full loop ${json.ok ? "PASS" : "partial"} · ${json.score}/100`);
      await refresh();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "demo failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section id="live-demo" className="chaos">
      <h2>Live demo — be Priya for one decision</h2>
      <p className="sub">
        Start the September claim. Jordan will pause on the $860 catering charge. Your answer becomes
        precedent and policy — then watch October get held and Jordan’s approve get denied.{" "}
        {error ? `API: ${error}` : ready ? "Connected." : "Connecting…"}{" "}
        <Link href="/suite/claims">Open Claims suite</Link>
      </p>

      <div className="grid">
        <button type="button" className="primary" disabled={busy} onClick={() => void startInteractive()}>
          <span className="label">{busy && !pending ? "Jordan working…" : "Start — pause for Priya"}</span>
          <span className="detail">Stage path: Jordan asks about $860 catering, then you answer as Priya</span>
        </button>
        <button type="button" className="ghost" disabled={busy} onClick={() => void runFullFast()}>
          <span className="label">Run full loop</span>
          <span className="detail">Auto-answers for judges / CI</span>
        </button>
        <button type="button" className="reset" onClick={() => void resetDemo()}>
          Reset
        </button>
      </div>

      {pending && (
        <div className="priya">
          <p className="who">{pending.who}</p>
          <p className="about">{pending.about}</p>
          <p className="q">{pending.question}</p>
          <div className="choices">
            <button
              type="button"
              className="exclude"
              disabled={busy}
              onClick={() => void answerAsPriya(EXCLUDE_ANSWER)}
            >
              No — staff celebration. Exclude it.
            </button>
            <button
              type="button"
              className="keep"
              disabled={busy}
              onClick={() =>
                void answerAsPriya("Keep it — participants were there; treat as program cost")
              }
            >
              Keep it (wrong path for demo)
            </button>
          </div>
          <p className="hint">On stage: choose Exclude — that’s the Hyphenate “handles a no.”</p>
        </div>
      )}

      {note && <p className="note">{note}</p>}
      {talk && <p className="talk">{talk}</p>}

      {hyphenate?.judging && (
        <ul className="judge">
          {Object.entries(hyphenate.judging).map(([k, v]) => (
            <li key={k} className={v ? "ok" : "no"}>
              <span>{v ? "YES" : "NO"}</span>
              {k.replace(/^\d+_/, "").replace(/_/g, " ")}
            </li>
          ))}
          {hyphenate.score != null && <li className="score">Hyphenate {hyphenate.score}/100</li>}
        </ul>
      )}

      {features.length > 0 && (
        <ul className="features">
          {features.slice(0, 6).map((f) => (
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

      {viz && !pending && (
        <div className="viz-slot">
          <ClaimsRiskViz data={viz} compact />
        </div>
      )}

      <style jsx>{`
        .chaos {
          padding: 1.5rem clamp(1.25rem, 4vw, 2.5rem) 1.5rem;
          scroll-margin-top: 4rem;
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.35rem;
          margin: 0 0 0.25rem;
        }
        .sub {
          margin: 0 0 1rem;
          color: var(--ink-muted);
          font-size: 0.9rem;
          max-width: 42rem;
          line-height: 1.4;
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
        .ghost {
          text-align: left;
          border-radius: 10px;
          padding: 1rem 1.15rem;
          color: var(--ink);
          cursor: pointer;
        }
        .primary {
          background: #1f3328;
          border: 1px solid var(--accent);
          max-width: 28rem;
        }
        .ghost {
          background: transparent;
          border: 1px solid var(--line);
          max-width: 16rem;
        }
        .primary:disabled,
        .ghost:disabled {
          opacity: 0.65;
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
        .priya {
          margin-top: 1rem;
          padding: 1.1rem 1.2rem;
          border-radius: 14px;
          border: 1px solid rgba(212, 180, 95, 0.45);
          background: linear-gradient(160deg, rgba(80, 60, 20, 0.35), rgba(10, 16, 14, 0.7));
          max-width: 40rem;
        }
        .who {
          margin: 0;
          font-weight: 700;
          font-size: 0.95rem;
        }
        .about {
          margin: 0.2rem 0 0.55rem;
          color: var(--ink-muted);
          font-size: 0.8rem;
        }
        .priya .q {
          margin: 0 0 0.85rem;
          font-size: 0.92rem;
          line-height: 1.4;
          color: #e8f2ec;
        }
        .choices {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }
        .exclude {
          background: #1f4d3a;
          color: #e8f2ec;
          border: 0;
          border-radius: 8px;
          padding: 0.7rem 1rem;
          font-weight: 600;
          cursor: pointer;
        }
        .keep {
          background: transparent;
          border: 1px dashed var(--line);
          color: var(--ink-muted);
          border-radius: 8px;
          padding: 0.65rem 0.9rem;
          font-size: 0.8rem;
          cursor: pointer;
        }
        .hint {
          margin: 0.65rem 0 0;
          font-size: 0.75rem;
          color: #d4b45f;
        }
        .note {
          margin: 0.75rem 0 0;
          font-size: 0.85rem;
          color: #9fd0ff;
        }
        .talk {
          margin: 0.35rem 0 0;
          font-size: 0.88rem;
          color: #c8e6d4;
          font-style: italic;
        }
        .judge {
          list-style: none;
          margin: 0.85rem 0 0;
          padding: 0;
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
        }
        .judge li {
          font-size: 0.72rem;
          padding: 0.3rem 0.55rem;
          border-radius: 6px;
          background: rgba(255, 255, 255, 0.05);
          display: flex;
          gap: 0.35rem;
          align-items: center;
        }
        .judge span {
          font-weight: 700;
          font-size: 0.62rem;
        }
        .judge .ok span {
          color: #5fd49a;
        }
        .judge .no span {
          color: #d45f5f;
        }
        .judge .score {
          color: #7eb892;
          font-weight: 700;
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
