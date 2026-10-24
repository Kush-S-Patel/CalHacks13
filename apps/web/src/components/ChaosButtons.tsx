"use client";

import { useWorld } from "@/hooks/useWorld";
import { injectChaos, resetDemo } from "@/lib/demo-store";

export function ChaosButtons() {
  const { ready, error } = useWorld();

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
          <span className="detail">Short wire · duplicate $4.2k · spike · late AR · $1.4k hold</span>
        </button>
        <button type="button" className="reset" onClick={() => void resetDemo()}>
          Reset to onboarded policies
        </button>
      </div>
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
        .primary {
          text-align: left;
          background: #1f3328;
          border: 1px solid var(--accent);
          border-radius: 10px;
          padding: 1rem 1.15rem;
          color: var(--ink);
          max-width: 28rem;
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