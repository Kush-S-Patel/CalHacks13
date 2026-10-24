"use client";

import { useState } from "react";
import { useWorld } from "@/hooks/useWorld";
import { injectChaos, resetDemo } from "@/lib/demo-store";

const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

export function ChaosButtons() {
  const { ready, error } = useWorld();
  const [missionNote, setMissionNote] = useState<string | null>(null);

  async function runMissionDemo() {
    setMissionNote("Running mission…");
    try {
      const res = await fetch(`${API}/v1/missions/demo`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      const ledger = json.job_ledger || {};
      setMissionNote(
        `Mission ${json.ok ? "OK" : "partial"} · score ${json.score}/100 · spend $${((ledger.spent_cents || 0) / 100).toFixed(2)} · margin $${((ledger.margin_cents || 0) / 100).toFixed(2)} · denials ${ledger.denial_count ?? 0}`,
      );
    } catch (e) {
      setMissionNote(e instanceof Error ? e.message : "mission demo failed");
    }
  }

  return (
    <section className="chaos">
      <h2>Run the system of work</h2>
      <p className="sub">
        Sync → learn policies → agents propose → ask/hold → owner decide → gateway post.
        {error ? ` API: ${error}` : ready ? " Connected." : " Connecting…"}
      </p>
      <div className="grid">
        <button type="button" className="primary" onClick={() => void injectChaos("full_demo")}>
          <span className="label">Inject full chaos + answer key</span>
          <span className="detail">
            Short wire · duplicate $4.2k · spike · late AR · $1.4k hold · Capital One Nessie bank rail
          </span>
        </button>
        <button type="button" className="mission" onClick={() => void runMissionDemo()}>
          <span className="label">Mission Margin demo</span>
          <span className="detail">$250 quote · $8 tool cap · hard deny · job-cost ledger</span>
        </button>
        <button type="button" className="reset" onClick={() => void resetDemo()}>
          Reset to onboarded policies
        </button>
      </div>
      {missionNote && <p className="mission-note">{missionNote}</p>}
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
        .reset {
          background: transparent;
          border: 1px dashed var(--line);
          color: var(--ink-muted);
          padding: 0.55rem 0.85rem;
          border-radius: 6px;
          font-size: 0.8rem;
        }
      `}</style>
    </section>
  );
}