"use client";

import { useEffect, useState } from "react";

const BEATS = [
  { id: "prep", label: "Prepare", detail: "Jordan builds rev 1" },
  { id: "ask", label: "Ask", detail: "$860 catering?" },
  { id: "no", label: "No", detail: "Priya excludes it" },
  { id: "learn", label: "Learn", detail: "Precedent → policy" },
  { id: "prove", label: "Prove", detail: "Deny · approve · audit" },
];

export function ConceptBanner() {
  const [beat, setBeat] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setBeat((b) => (b + 1) % BEATS.length), 2200);
    return () => clearInterval(t);
  }, []);

  return (
    <header className="banner">
      <div className="plane" aria-hidden>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/claims-hero-banner.jpg" alt="" className="photo" />
        <div className="veil" />
        <div className="scan" />
      </div>

      <div className="content">
        <p className="brand">SwarmCFO Claims</p>
        <h1>
          A reimbursement package that
          <span className="accent"> learns from a no</span>
        </h1>
        <p className="lede">
          Meridian Bookkeeping prepares federal grant claims for nonprofits. The agent matches the
          ledger, asks the manager the hard question, remembers the answer, and improves next month —
          without ever submitting or touching the ledger.
        </p>

        <div className="loop" role="img" aria-label="Animated learning loop: prepare, ask, no, learn, prove">
          {BEATS.map((b, i) => (
            <div key={b.id} className={`node ${i === beat ? "on" : i < beat ? "done" : ""}`}>
              <span className="dot" />
              <strong>{b.label}</strong>
              <small>{b.detail}</small>
            </div>
          ))}
          <div className="rail" aria-hidden>
            <div className="fill" style={{ width: `${((beat + 1) / BEATS.length) * 100}%` }} />
          </div>
        </div>

        <div className="cta">
          <a href="#live-demo" className="primary">
            Run the live demo
          </a>
          <a href="#how-it-works" className="ghost">
            How it works
          </a>
        </div>
      </div>

      <style jsx>{`
        .banner {
          position: relative;
          min-height: min(92vh, 820px);
          display: flex;
          align-items: flex-end;
          overflow: hidden;
          border-bottom: 1px solid var(--line);
        }
        .plane {
          position: absolute;
          inset: 0;
          z-index: 0;
        }
        .photo {
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: center 35%;
          display: block;
          transform: scale(1.04);
          animation: drift 28s ease-in-out infinite alternate;
        }
        .veil {
          position: absolute;
          inset: 0;
          background:
            linear-gradient(105deg, rgba(8, 12, 10, 0.92) 0%, rgba(8, 12, 10, 0.72) 42%, rgba(8, 12, 10, 0.35) 100%),
            linear-gradient(0deg, rgba(8, 12, 10, 0.85) 0%, transparent 45%);
        }
        .scan {
          position: absolute;
          left: 0;
          right: 0;
          height: 28%;
          top: -30%;
          background: linear-gradient(
            180deg,
            transparent,
            rgba(95, 212, 154, 0.07),
            transparent
          );
          animation: sweep 7s ease-in-out infinite;
          pointer-events: none;
        }
        .content {
          position: relative;
          z-index: 1;
          padding: clamp(2rem, 5vw, 3.5rem) clamp(1.25rem, 4vw, 2.5rem) 2.5rem;
          max-width: 44rem;
        }
        .brand {
          font-family: var(--font-display);
          font-size: clamp(2.6rem, 7vw, 4.6rem);
          font-weight: 700;
          letter-spacing: -0.035em;
          margin: 0 0 0.65rem;
          line-height: 0.95;
          animation: rise 0.9s ease both;
        }
        h1 {
          font-family: var(--font-display);
          font-size: clamp(1.35rem, 3.2vw, 2rem);
          font-weight: 500;
          margin: 0 0 0.85rem;
          line-height: 1.25;
          max-width: 22ch;
          animation: rise 0.9s ease 0.08s both;
        }
        .accent {
          color: var(--accent-bright);
        }
        .lede {
          margin: 0 0 1.5rem;
          color: var(--ink-muted);
          font-size: 1.02rem;
          line-height: 1.5;
          max-width: 38rem;
          animation: rise 0.9s ease 0.16s both;
        }
        .loop {
          position: relative;
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 0.45rem;
          margin-bottom: 1.5rem;
          padding-bottom: 0.85rem;
          animation: rise 0.9s ease 0.24s both;
        }
        .rail {
          position: absolute;
          left: 0.4rem;
          right: 0.4rem;
          bottom: 0;
          height: 2px;
          background: rgba(255, 255, 255, 0.08);
          border-radius: 2px;
          overflow: hidden;
        }
        .fill {
          height: 100%;
          background: var(--accent-bright);
          transition: width 0.6s ease;
        }
        .node {
          text-align: left;
          opacity: 0.4;
          transition: opacity 0.4s ease, transform 0.4s ease;
        }
        .node.done {
          opacity: 0.75;
        }
        .node.on {
          opacity: 1;
          transform: translateY(-2px);
        }
        .dot {
          display: block;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.25);
          margin-bottom: 0.45rem;
        }
        .node.on .dot {
          background: var(--accent-bright);
          box-shadow: 0 0 0 4px rgba(95, 212, 154, 0.2);
        }
        .node strong {
          display: block;
          font-size: 0.78rem;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          margin-bottom: 0.15rem;
        }
        .node small {
          display: block;
          font-size: 0.72rem;
          color: var(--ink-muted);
          line-height: 1.25;
        }
        .cta {
          display: flex;
          flex-wrap: wrap;
          gap: 0.65rem;
          animation: rise 0.9s ease 0.32s both;
        }
        .primary,
        .ghost {
          display: inline-flex;
          align-items: center;
          padding: 0.75rem 1.15rem;
          border-radius: 8px;
          font-weight: 600;
          font-size: 0.92rem;
        }
        .primary {
          background: #1f4d3a;
          color: #e8f2ec;
          border: 1px solid rgba(95, 212, 154, 0.45);
        }
        .ghost {
          border: 1px solid var(--line);
          color: var(--ink-muted);
          background: rgba(0, 0, 0, 0.25);
        }
        @media (max-width: 640px) {
          .loop {
            grid-template-columns: repeat(2, 1fr);
          }
          .node:last-child {
            grid-column: span 2;
          }
        }
        @keyframes drift {
          from {
            transform: scale(1.04) translate3d(0, 0, 0);
          }
          to {
            transform: scale(1.08) translate3d(-1.5%, 1%, 0);
          }
        }
        @keyframes sweep {
          0% {
            top: -30%;
          }
          100% {
            top: 110%;
          }
        }
        @keyframes rise {
          from {
            opacity: 0;
            transform: translateY(12px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </header>
  );
}
