"use client";

import { useState } from "react";
import { useWorld } from "@/hooks/useWorld";
import { refresh, resetDemo } from "@/lib/demo-store";
import { ClaimsRiskViz, type RiskVizData } from "@/components/suite/ClaimsRiskViz";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

export function ChaosButtons() {
  const { ready, error } = useWorld();
  const [missionNote, setMissionNote] = useState<string | null>(null);
  const [viz, setViz] = useState<RiskVizData | null>(null);
  const [features, setFeatures] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function runClaimsDemo() {
    setBusy(true);
    setMissionNote("Preparing reimbursement claim + rejection risk…");
    try {
      const res = await fetch(`${API}/v1/claims/demo`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      const risk = json.risk || {};
      if (json.viz) setViz(json.viz as RiskVizData);
      setFeatures((json.answer_key?.features as string[]) || []);
      setMissionNote(
        `Claims ${json.ok ? "OK" : "partial"} · checks ${json.score}/100 · rejection risk ${risk.score ?? "—"} (${risk.band ?? "—"}) · ${(json.claim?.exceptions || []).length} exceptions`,
      );
    } catch (e) {
      setMissionNote(e instanceof Error ? e.message : "claims demo failed");
    } finally {
      setBusy(false);
    }
  }

  async function runFullDemo() {
    setBusy(true);
    setMissionNote("Running Claims + SoW full demo…");
    try {
      const res = await fetch(`${API}/v1/demo/run`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      const claims = json.claims || {};
      const vizPayload = (json.viz || claims.viz) as RiskVizData | undefined;
      if (vizPayload) setViz(vizPayload);
      setFeatures(
        (claims.answer_key?.features as string[]) ||
          (json.answer_key?.features as string[]) ||
          [],
      );
      const risk = json.risk || claims.risk || {};
      setMissionNote(
        `Full demo · Claims checks ${claims.score ?? json.score}/100 · risk ${risk.score ?? "—"} (${risk.band ?? "—"}) · SoW score ${json.sow_score?.hyphenate_score ?? "—"}`,
      );
      await refresh();
    } catch (e) {
      setMissionNote(e instanceof Error ? e.message : "full demo failed");
    } finally {
      setBusy(false);
    }
  }

  async function runMissionDemo() {
    setMissionNote("Running mission…");
    try {
      const res = await fetch(`${API}/v1/missions/demo`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      const ledger = json.job_ledger || {};
      setMissionNote(
        `Mission ${json.ok ? "OK" : "partial"} · score ${json.score}/100 · spend $${((ledger.spent_cents || 0) / 100).toFixed(2)} · margin $${((ledger.margin_cents || 0) / 100).toFixed(2)}`,
      );
    } catch (e) {
      setMissionNote(e instanceof Error ? e.message : "mission demo failed");
    }
  }

  return (
    <section className="chaos">
      <h2>SwarmCFO Claims — run the work</h2>
      <p className="sub">
        Award rules → match GL to evidence → compliance exceptions → rejection risk score → manager
        approve. {error ? ` API: ${error}` : ready ? " Connected." : " Connecting…"}{" "}
        <Link href="/suite/claims">Open Claims suite</Link>
      </p>
      <div className="grid">
        <button type="button" className="primary" disabled={busy} onClick={() => void runClaimsDemo()}>
          <span className="label">{busy ? "Running…" : "Prepare reimbursement claim"}</span>
          <span className="detail">
            Workforce grant Sep package · FAC / CA / Grants.gov / CA awards / 990 priors · risk gauge
          </span>
        </button>
        <button type="button" className="mission" disabled={busy} onClick={() => void runFullDemo()}>
          <span className="label">Full demo (Claims + SoW)</span>
          <span className="detail">Risk-scored claim package then bakery control-plane chaos</span>
        </button>
        <button type="button" className="mission" onClick={() => void runMissionDemo()}>
          <span className="label">Mission Margin (secondary)</span>
          <span className="detail">$250 quote · $8 tool cap · job-cost ledger</span>
        </button>
        <button type="button" className="reset" onClick={() => void resetDemo()}>
          Reset
        </button>
      </div>
      {missionNote && <p className="mission-note">{missionNote}</p>}

      {features.length > 0 && (
        <ul className="features">
          {features.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
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
        .mission {
          text-align: left;
          background: #1f3328;
          border: 1px solid var(--accent);
          border-radius: 10px;
          padding: 1rem 1.15rem;
          color: var(--ink);
          max-width: 28rem;
          cursor: pointer;
        }
        .primary:disabled,
        .mission:disabled {
          opacity: 0.65;
          cursor: wait;
        }
        .mission {
          border-color: #3d6b8a;
          background: #152530;
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
        .mission-note {
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
