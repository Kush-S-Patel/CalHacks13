"use client";

import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

type MissionSummary = {
  id: string;
  client: string;
  brief: string;
  status: string;
  quote_cents: number;
  max_spend_cents: number;
  spent_cents: number;
  margin_cents: number;
  denial_count: number;
  evidence_count: number;
};

type MissionDetail = {
  id: string;
  client: string;
  status: string;
  brief: string;
  deliverable_md: string;
  exceptions: string[];
  denials: { agent: string; tool: string; amount_cents: number; reason: string }[];
  job_ledger: {
    quote_cents: number;
    max_spend_cents: number;
    spent_cents: number;
    remaining_cents: number;
    margin_cents: number;
    margin_pct: number;
    by_agent_cents: Record<string, number>;
    by_tool_cents: Record<string, number>;
    denial_count: number;
  };
  log: string[];
};

function usd(cents: number) {
  return `$${(cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function JobsPanel() {
  const [list, setList] = useState<MissionSummary[]>([]);
  const [selected, setSelected] = useState<MissionDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [demoScore, setDemoScore] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/v1/missions`, { cache: "no-store" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setList(json.missions || []);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "missions offline");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function openMission(id: string) {
    const res = await fetch(`${API}/v1/missions/${encodeURIComponent(id)}`, { cache: "no-store" });
    if (!res.ok) {
      setErr(await res.text());
      return;
    }
    const json = await res.json();
    setSelected(json.mission as MissionDetail);
  }

  async function runDemo() {
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch(`${API}/v1/missions/demo`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setDemoScore(json.score ?? null);
      await load();
      if (json.mission?.id) await openMission(json.mission.id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "demo failed");
    } finally {
      setBusy(false);
    }
  }

  async function expandBudget() {
    if (!selected) return;
    setBusy(true);
    try {
      const res = await fetch(`${API}/v1/missions/${selected.id}/expand-budget`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ additional_cents: 200, reason: "owner expand +$2" }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setSelected(json.mission);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "expand failed");
    } finally {
      setBusy(false);
    }
  }

  const ledger = selected?.job_ledger;

  return (
    <section className="jobs">
      <header>
        <div>
          <h1>Mission Margin Controller</h1>
          <p>
            Fixed-price jobs with hard tool budgets. Agents research, extract, and verify under
            code-enforced spend limits — then you get the deliverable plus a job-cost ledger.
          </p>
        </div>
        <button type="button" disabled={busy} onClick={() => void runDemo()}>
          {busy ? "Running…" : "Inject mission demo ($250 / $8)"}
        </button>
      </header>

      {demoScore != null && <p className="score">Demo score {demoScore}/100</p>}
      {err && <p className="err">{err}</p>}

      <div className="layout">
        <ul className="list">
          {list.length === 0 && <li className="empty">No missions yet — run the answer-key demo.</li>}
          {list.map((m) => (
            <li key={m.id}>
              <button
                type="button"
                className={selected?.id === m.id ? "on" : ""}
                onClick={() => void openMission(m.id)}
              >
                <strong>{m.client}</strong>
                <span>
                  {m.status} · quote {usd(m.quote_cents)} · spend {usd(m.spent_cents)} · margin{" "}
                  {usd(m.margin_cents)}
                </span>
              </button>
            </li>
          ))}
        </ul>

        <div className="detail">
          {!selected && <p className="empty">Select a mission to inspect the job ledger.</p>}
          {selected && ledger && (
            <>
              <h2>{selected.client}</h2>
              <p className="meta">{selected.brief}</p>
              <p className="status">
                Status <strong>{selected.status}</strong>
                {selected.status === "held" && (
                  <button type="button" className="expand" disabled={busy} onClick={() => void expandBudget()}>
                    Expand budget +$2 &amp; finish
                  </button>
                )}
              </p>

              <div className="kpis">
                <article>
                  <span>Quote</span>
                  <p>{usd(ledger.quote_cents)}</p>
                </article>
                <article>
                  <span>Tool spend</span>
                  <p>{usd(ledger.spent_cents)}</p>
                </article>
                <article>
                  <span>Max spend</span>
                  <p>{usd(ledger.max_spend_cents)}</p>
                </article>
                <article>
                  <span>Margin</span>
                  <p className="up">
                    {usd(ledger.margin_cents)} ({ledger.margin_pct}%)
                  </p>
                </article>
              </div>

              {selected.denials?.length > 0 && (
                <>
                  <h3>Budget denials</h3>
                  <ul className="denials">
                    {selected.denials.map((d, i) => (
                      <li key={i}>
                        DENIED {d.agent}/{d.tool} {usd(d.amount_cents)} — {d.reason}
                      </li>
                    ))}
                  </ul>
                </>
              )}

              <h3>Deliverable</h3>
              <pre className="md">{selected.deliverable_md || "(empty)"}</pre>
            </>
          )}
        </div>
      </div>

      <style jsx>{`
        .jobs {
          padding: 1.5rem 2rem 3rem;
          max-width: 1200px;
        }
        header {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-start;
          margin-bottom: 1rem;
        }
        h1 {
          font-family: var(--font-display);
          font-size: 1.75rem;
          margin: 0 0 0.35rem;
        }
        header p {
          color: var(--ink-muted);
          max-width: 36rem;
          margin: 0;
          font-size: 0.92rem;
        }
        header button,
        .expand {
          background: #1f4d3a;
          color: #e8f2ec;
          border: 0;
          border-radius: 8px;
          padding: 0.65rem 1rem;
          font-weight: 600;
          cursor: pointer;
        }
        header button:disabled,
        .expand:disabled {
          opacity: 0.6;
        }
        .score {
          color: #7eb892;
          font-weight: 600;
        }
        .err {
          color: var(--warn);
        }
        .layout {
          display: grid;
          grid-template-columns: minmax(220px, 320px) 1fr;
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
        .list button span,
        .meta {
          color: var(--ink-muted);
          font-size: 0.8rem;
        }
        .detail {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 1.25rem 1.4rem;
          background: rgba(12, 18, 16, 0.4);
        }
        .detail h2 {
          margin: 0 0 0.35rem;
          font-family: var(--font-display);
        }
        .status {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          flex-wrap: wrap;
        }
        .expand {
          padding: 0.4rem 0.75rem;
          font-size: 0.8rem;
        }
        .kpis {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 0.75rem;
          margin: 1rem 0;
        }
        @media (max-width: 700px) {
          .kpis {
            grid-template-columns: 1fr 1fr;
          }
        }
        .kpis article {
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 0.65rem 0.75rem;
        }
        .kpis span {
          font-size: 0.65rem;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--ink-muted);
        }
        .kpis p {
          margin: 0.25rem 0 0;
          font-family: var(--font-mono, ui-monospace, monospace);
          font-size: 1.05rem;
        }
        .up {
          color: #7eb892;
        }
        h3 {
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--ink-muted);
        }
        .denials {
          list-style: none;
          padding: 0;
          margin: 0 0 1rem;
          font-size: 0.82rem;
          color: #e8b4a0;
        }
        .md {
          white-space: pre-wrap;
          font-size: 0.78rem;
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
