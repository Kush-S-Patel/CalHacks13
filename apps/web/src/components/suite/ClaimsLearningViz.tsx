"use client";

export type LearningStoryStep = {
  step: number;
  actor: string;
  action: string;
  detail?: unknown;
  question?: string;
  answer?: string;
  spoken?: string;
  denied?: boolean;
  why?: string;
  policy_id?: string;
  precedent_id?: string;
  excluded_cents?: number;
  eligible_cents?: number;
};

export type LearningResults = {
  excluded_usd?: number;
  receipt_attached_usd?: number;
  eligible_reimbursement_usd?: number;
  critical_exceptions_before?: number;
  critical_exceptions_after?: number;
  unauthorized_approvals?: number;
  agent_approve_denied?: boolean;
  denial_message?: string | null;
  policy_id?: string;
  policy_version?: number;
  next_month_held?: boolean;
  audit_events_for_claim?: number;
};

export type AuditRow = {
  id?: string;
  at?: string;
  actor: string;
  action: string;
  subject: string;
  allowed: boolean;
  reason: string;
  diff?: Record<string, unknown>;
};

function usd(n: number | undefined) {
  if (n == null) return "—";
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function ClaimsLearningViz({
  story,
  results,
  checks,
  audit,
  revisionDiff,
  outcome,
}: {
  story?: LearningStoryStep[];
  results?: LearningResults | null;
  checks?: Record<string, boolean>;
  audit?: AuditRow[];
  revisionDiff?: { from?: Record<string, unknown>; to?: Record<string, unknown> } | null;
  outcome?: string;
}) {
  if (!story?.length && !results) return null;

  return (
    <section className="learn">
      {outcome && <p className="outcome">{outcome}</p>}

      {results && (
        <div className="kpis">
          <article>
            <span>Excluded / moved out</span>
            <strong className="mono">{usd(results.excluded_usd)}</strong>
          </article>
          <article>
            <span>Receipt attached</span>
            <strong className="mono">{usd(results.receipt_attached_usd)}</strong>
          </article>
          <article className="good">
            <span>Eligible reimbursement</span>
            <strong className="mono">{usd(results.eligible_reimbursement_usd)}</strong>
          </article>
          <article>
            <span>Critical exceptions</span>
            <strong className="mono">
              {results.critical_exceptions_before ?? 4} → {results.critical_exceptions_after ?? 0}
            </strong>
          </article>
          <article className={results.unauthorized_approvals === 0 ? "good" : "bad"}>
            <span>Unauthorized approvals</span>
            <strong className="mono">{results.unauthorized_approvals ?? "—"}</strong>
          </article>
          <article className={results.agent_approve_denied ? "good" : "bad"}>
            <span>Agent approve</span>
            <strong>{results.agent_approve_denied ? "DENIED" : "FAIL"}</strong>
          </article>
        </div>
      )}

      {story && story.length > 0 && (
        <div className="story">
          <h3>Learning loop</h3>
          <ol>
            {story.map((s, i) => (
              <li key={`${s.step}-${i}`} className={s.denied ? "denied" : ""}>
                <span className="n">{s.step}</span>
                <div>
                  <strong>
                    {s.actor}
                    <span className="act-tag">{s.action.replace(/_/g, " ")}</span>
                  </strong>
                  {s.spoken && <p className="spoken">“{s.spoken}”</p>}
                  {s.question && <p className="q">Ask: {s.question}</p>}
                  {s.answer && <p className="a">Answer: {s.answer}</p>}
                  {s.denied && <p className="deny">DENIED — {s.why}</p>}
                  {s.policy_id && <p className="meta">Policy {s.policy_id}</p>}
                  {s.precedent_id && <p className="meta">Precedent {s.precedent_id}</p>}
                  {typeof s.detail === "string" && <p className="meta">{s.detail}</p>}
                  {Array.isArray(s.detail) && (
                    <p className="meta">{(s.detail as string[]).join(" · ")}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="split">
        {revisionDiff && (
          <article className="card">
            <h3>Revision diff</h3>
            <div className="diff">
              <div>
                <span>Rev 1</span>
                <pre>{JSON.stringify(revisionDiff.from, null, 2)}</pre>
              </div>
              <div>
                <span>Rev 2</span>
                <pre>{JSON.stringify(revisionDiff.to, null, 2)}</pre>
              </div>
            </div>
          </article>
        )}

        {checks && (
          <article className="card">
            <h3>Answer-key checks</h3>
            <ul className="checks">
              {Object.entries(checks).map(([k, v]) => (
                <li key={k} className={v ? "ok" : "no"}>
                  <span>{v ? "PASS" : "GAP"}</span>
                  {k.replace(/_/g, " ")}
                </li>
              ))}
            </ul>
          </article>
        )}
      </div>

      {audit && audit.length > 0 && (
        <article className="card">
          <h3>Claim audit (append-only)</h3>
          <ul className="aud">
            {audit.map((e, i) => (
              <li key={e.id || i} className={e.allowed === false ? "denied" : ""}>
                <span className="act">{e.action}</span>
                <div>
                  <strong>{e.actor}</strong>
                  <p>
                    {e.subject}: {e.reason}
                  </p>
                  {e.allowed === false && <em>DENIED</em>}
                  {e.diff && Object.keys(e.diff).length > 0 && (
                    <pre className="tiny">{JSON.stringify(e.diff, null, 0).slice(0, 280)}</pre>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </article>
      )}

      <style jsx>{`
        .learn {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .outcome {
          margin: 0;
          padding: 0.85rem 1rem;
          border-radius: 10px;
          border: 1px solid rgba(95, 212, 154, 0.4);
          background: rgba(61, 155, 106, 0.12);
          color: #c8e6d4;
          font-size: 0.9rem;
          line-height: 1.4;
        }
        .kpis {
          display: grid;
          grid-template-columns: repeat(6, minmax(0, 1fr));
          gap: 0.55rem;
        }
        @media (max-width: 900px) {
          .kpis {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        .kpis article {
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 10px;
          padding: 0.7rem 0.8rem;
          background: rgba(10, 16, 14, 0.55);
        }
        .kpis span {
          display: block;
          font-size: 0.62rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--ink-muted, #9ab0a4);
          margin-bottom: 0.25rem;
        }
        .kpis strong {
          font-size: 1.05rem;
        }
        .kpis .good {
          border-color: rgba(95, 212, 154, 0.45);
        }
        .kpis .bad {
          border-color: rgba(212, 95, 95, 0.45);
        }
        .story h3,
        .card h3 {
          margin: 0 0 0.65rem;
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--ink-muted, #9ab0a4);
        }
        .story ol {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
        }
        .story li {
          display: grid;
          grid-template-columns: 2rem 1fr;
          gap: 0.65rem;
          padding: 0.65rem 0.8rem;
          border-radius: 10px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(10, 16, 14, 0.45);
        }
        .story li.denied {
          border-color: rgba(212, 95, 95, 0.5);
        }
        .n {
          font-family: ui-monospace, monospace;
          color: #7eb892;
          font-weight: 700;
        }
        .act-tag {
          margin-left: 0.45rem;
          font-weight: 500;
          font-size: 0.72rem;
          color: var(--ink-muted, #9ab0a4);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .spoken {
          margin: 0.35rem 0 0;
          font-size: 0.88rem;
          color: #e8f2ec;
          font-style: italic;
          line-height: 1.35;
        }
        .q {
          color: #9fd0ff;
          margin: 0.25rem 0 0;
          font-size: 0.82rem;
        }
        .a {
          color: #d4b45f;
          margin: 0.2rem 0 0;
          font-size: 0.82rem;
        }
        .deny {
          color: #d45f5f;
          font-weight: 700;
          margin: 0.25rem 0 0;
          font-size: 0.8rem;
        }
        .meta {
          margin: 0.2rem 0 0;
          font-size: 0.75rem;
          color: var(--ink-muted, #9ab0a4);
        }
        .split {
          display: grid;
          grid-template-columns: 1.4fr 1fr;
          gap: 0.85rem;
        }
        @media (max-width: 800px) {
          .split {
            grid-template-columns: 1fr;
          }
        }
        .card {
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 0.9rem 1rem;
          background: rgba(10, 16, 14, 0.55);
        }
        .diff {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.5rem;
        }
        .diff span {
          font-size: 0.65rem;
          text-transform: uppercase;
          color: var(--ink-muted, #9ab0a4);
        }
        .diff pre,
        .tiny {
          font-size: 0.65rem;
          overflow: auto;
          max-height: 180px;
          background: #070b09;
          padding: 0.5rem;
          border-radius: 6px;
          margin: 0.25rem 0 0;
        }
        .checks {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 0.3rem;
        }
        .checks li {
          font-size: 0.75rem;
          display: flex;
          gap: 0.45rem;
        }
        .checks span {
          font-size: 0.62rem;
          font-weight: 700;
          padding: 0.1rem 0.3rem;
          border-radius: 3px;
          background: rgba(255, 255, 255, 0.06);
        }
        .checks .ok span {
          color: #5fd49a;
        }
        .checks .no span {
          color: #d45f5f;
        }
        .aud {
          list-style: none;
          margin: 0;
          padding: 0;
          max-height: 280px;
          overflow: auto;
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }
        .aud li {
          display: grid;
          grid-template-columns: 5.5rem 1fr;
          gap: 0.5rem;
          font-size: 0.78rem;
          padding: 0.45rem 0.55rem;
          border-left: 2px solid #3d9b6a;
          background: rgba(26, 42, 34, 0.4);
        }
        .aud li.denied {
          border-left-color: #d45f5f;
        }
        .act {
          font-size: 0.62rem;
          text-transform: uppercase;
          color: var(--ink-muted, #9ab0a4);
          font-weight: 700;
        }
        .aud p {
          margin: 0.15rem 0 0;
          color: var(--ink-muted, #9ab0a4);
        }
        .aud em {
          color: #d45f5f;
          font-style: normal;
          font-weight: 700;
          font-size: 0.7rem;
        }
      `}</style>
    </section>
  );
}
