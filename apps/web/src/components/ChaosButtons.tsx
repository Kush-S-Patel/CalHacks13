"use client";

import { CHAOS_BUTTONS } from "@swarmcfo/shared";
import { useWorld } from "@/hooks/useWorld";
import { injectChaos, resetDemo } from "@/lib/demo-store";

export function ChaosButtons() {
  const { chaosInjected } = useWorld();

  return (
    <section className="chaos">
      <h2>Inject chaos</h2>
      <p className="sub">Judges press these — or join from phone via QR.</p>
      <div className="grid">
        {CHAOS_BUTTONS.map((b) => {
          const done = chaosInjected.includes(b.kind);
          return (
            <button
              key={b.kind}
              type="button"
              disabled={done}
              onClick={() => void injectChaos(b.kind)}
            >
              <span className="label">{b.label}</span>
              <span className="detail">{done ? "Injected" : b.detail}</span>
            </button>
          );
        })}
      </div>
      <button type="button" className="reset" onClick={resetDemo}>
        Reset demo
      </button>
      <style jsx>{`
        .chaos {
          padding: 0 2rem 1.5rem;
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
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 0.65rem;
        }
        .grid button {
          text-align: left;
          background: var(--bg-panel);
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 1rem;
          color: var(--ink);
          transition: border-color 0.15s ease, background 0.15s ease;
        }
        .grid button:not(:disabled):hover {
          border-color: var(--accent);
          background: #1f3328;
        }
        .grid button:disabled {
          opacity: 0.55;
          cursor: default;
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
          margin-top: 0.85rem;
          background: transparent;
          border: 1px dashed var(--line);
          color: var(--ink-muted);
          padding: 0.45rem 0.85rem;
          border-radius: 6px;
          font-size: 0.8rem;
        }
      `}</style>
    </section>
  );
}