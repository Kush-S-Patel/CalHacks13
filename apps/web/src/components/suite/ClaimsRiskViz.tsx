"use client";

export type RiskVizDriver = {
  exception?: string;
  points?: number;
  count?: number;
  sources?: { corpus?: string; note?: string }[];
};

export type RiskVizData = {
  score: number;
  band: string;
  recommendation?: string;
  drivers?: RiskVizDriver[];
  exceptions?: { code?: string; message?: string }[];
  corpus?: Record<string, unknown>;
  nonprofit?: string;
  claimed_cents?: number;
  checks?: Record<string, boolean>;
};

const BAND_COLOR: Record<string, string> = {
  low: "#5fd49a",
  moderate: "#d4b45f",
  high: "#d4895f",
  critical: "#d45f5f",
};

function corpusBars(corpus: Record<string, unknown> | undefined) {
  if (!corpus) return [];
  return [
    { id: "fac", label: "FAC findings", value: Number(corpus.fac_findings || 0), hint: "audit / allowability" },
    { id: "ca_denied", label: "CA denial taxonomy", value: Number(corpus.ca_denied_rows || 0), hint: "submission priors" },
    { id: "gg", label: "Grants.gov-shaped", value: Number(corpus.grants_gov_rejection_rows || 0), hint: "schema / SAM" },
    { id: "ca_grants", label: "CA Grants awards", value: Number(corpus.ca_grants_awards || 0), hint: "funding links" },
    { id: "irs", label: "IRS 990 index", value: Number(corpus.irs990_index_rows || 0), hint: "EIN inventory" },
    { id: "pp", label: "ProPublica orgs", value: Number(corpus.propublica_orgs || 0), hint: "990 financials" },
  ];
}

function exceptionCounts(exceptions: { code?: string }[] | undefined) {
  const map = new Map<string, number>();
  for (const ex of exceptions || []) {
    const code = ex.code || "other";
    map.set(code, (map.get(code) || 0) + 1);
  }
  return [...map.entries()]
    .map(([code, n]) => ({ code, n }))
    .sort((a, b) => b.n - a.n);
}

function RiskGauge({ score, band }: { score: number; band: string }) {
  const clamped = Math.max(0, Math.min(100, score));
  const r = 54;
  const c = 2 * Math.PI * r;
  const dash = (clamped / 100) * c * 0.75;
  const gap = c - dash;
  const color = BAND_COLOR[band] || BAND_COLOR.moderate;
  return (
    <div className="gauge">
      <svg viewBox="0 0 140 110" aria-label={`Rejection risk ${score} of 100, ${band}`}>
        <path
          d="M 16 90 A 54 54 0 1 1 124 90"
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <path
          d="M 16 90 A 54 54 0 1 1 124 90"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${gap}`}
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
        <text x="70" y="68" textAnchor="middle" className="g-score">
          {score}
        </text>
        <text x="70" y="86" textAnchor="middle" className="g-band">
          {band}
        </text>
      </svg>
      <style jsx>{`
        .gauge {
          display: flex;
          justify-content: center;
        }
        svg {
          width: 160px;
          height: 126px;
        }
        :global(.g-score) {
          fill: #e8f2ec;
          font-size: 28px;
          font-weight: 700;
          font-family: var(--font-display, Georgia, serif);
        }
        :global(.g-band) {
          fill: ${color};
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }
      `}</style>
    </div>
  );
}

function BarRow({
  label,
  value,
  max,
  color,
  suffix,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
  suffix?: string;
}) {
  const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  return (
    <div className="bar-row">
      <div className="lab">
        <span>{label}</span>
        <span className="mono">
          {value}
          {suffix || ""}
        </span>
      </div>
      <div className="track">
        <div className="fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <style jsx>{`
        .bar-row {
          margin-bottom: 0.55rem;
        }
        .lab {
          display: flex;
          justify-content: space-between;
          font-size: 0.78rem;
          margin-bottom: 0.2rem;
          gap: 0.5rem;
        }
        .lab span:first-child {
          color: var(--ink-muted, #9ab0a4);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .mono {
          font-family: ui-monospace, monospace;
          color: var(--ink, #e8f2ec);
        }
        .track {
          height: 8px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.06);
          overflow: hidden;
        }
        .fill {
          height: 100%;
          border-radius: 999px;
          transition: width 0.5s ease;
        }
      `}</style>
    </div>
  );
}

const PIPELINE = [
  "Award rules",
  "GL ↔ evidence",
  "Exceptions",
  "Validate",
  "Risk score",
  "Manager",
];

export function ClaimsRiskViz({ data, compact }: { data: RiskVizData; compact?: boolean }) {
  const color = BAND_COLOR[data.band] || BAND_COLOR.moderate;
  const drivers = (data.drivers || [])
    .filter((d) => (d.points || 0) > 0 || d.exception)
    .slice()
    .sort((a, b) => (b.points || 0) - (a.points || 0));
  const driverMax = Math.max(1, ...drivers.map((d) => d.points || 0));
  const bars = corpusBars(data.corpus);
  const barMax = Math.max(1, ...bars.map((b) => b.value));
  const exCounts = exceptionCounts(data.exceptions);
  const exMax = Math.max(1, ...exCounts.map((e) => e.n));
  const checkEntries = Object.entries(data.checks || {});

  return (
    <section className={`viz ${compact ? "compact" : ""}`}>
      <div className="pipeline" aria-label="Claims workflow">
        {PIPELINE.map((step, i) => (
          <span key={step} className={i === 4 ? "active" : ""}>
            {step}
            {i < PIPELINE.length - 1 && <i aria-hidden>→</i>}
          </span>
        ))}
      </div>

      <div className="top">
        <article className="card gauge-card">
          <h3>Rejection risk</h3>
          <RiskGauge score={data.score} band={data.band} />
          {data.nonprofit && <p className="who">{data.nonprofit}</p>}
          {data.recommendation && <p className="rec">{data.recommendation}</p>}
        </article>

        <article className="card">
          <h3>Score drivers</h3>
          {drivers.length === 0 && <p className="empty">No risk drivers yet — run the demo.</p>}
          {drivers.slice(0, compact ? 5 : 8).map((d) => (
            <BarRow
              key={`${d.exception}-${d.points}`}
              label={(d.exception || "driver").replace(/_/g, " ")}
              value={d.points || 0}
              max={driverMax}
              color={color}
              suffix=" pts"
            />
          ))}
        </article>

        <article className="card">
          <h3>Exception mix</h3>
          {exCounts.length === 0 && <p className="empty">No exceptions flagged.</p>}
          {exCounts.slice(0, compact ? 5 : 8).map((e) => (
            <BarRow
              key={e.code}
              label={e.code.replace(/_/g, " ")}
              value={e.n}
              max={exMax}
              color="#7eb8d4"
            />
          ))}
        </article>
      </div>

      <div className="bottom">
        <article className="card wide">
          <h3>Corpus coverage (risk priors)</h3>
          <div className="corpus-grid">
            {bars.map((b) => {
              const h = Math.max(8, Math.round((b.value / barMax) * 72));
              return (
                <div key={b.id} className="corp">
                  <div className="col" title={`${b.value} rows`}>
                    <div className="stem" style={{ height: `${h}px` }} />
                  </div>
                  <strong className="mono">{b.value.toLocaleString()}</strong>
                  <span>{b.label}</span>
                  <small>{b.hint}</small>
                </div>
              );
            })}
          </div>
        </article>

        {checkEntries.length > 0 && (
          <article className="card">
            <h3>Demo answer-key checks</h3>
            <ul className="checks">
              {checkEntries.map(([k, v]) => (
                <li key={k} className={v ? "ok" : "no"}>
                  <span>{v ? "PASS" : "GAP"}</span>
                  {k.replace(/_/g, " ")}
                </li>
              ))}
            </ul>
          </article>
        )}
      </div>

      <style jsx>{`
        .viz {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .pipeline {
          display: flex;
          flex-wrap: wrap;
          gap: 0.35rem 0.5rem;
          align-items: center;
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--ink-muted, #9ab0a4);
        }
        .pipeline .active {
          color: ${color};
          font-weight: 700;
        }
        .pipeline i {
          margin-left: 0.45rem;
          font-style: normal;
          opacity: 0.45;
        }
        .top,
        .bottom {
          display: grid;
          gap: 0.85rem;
        }
        .top {
          grid-template-columns: minmax(180px, 220px) 1fr 1fr;
        }
        .bottom {
          grid-template-columns: 1.6fr 1fr;
        }
        @media (max-width: 900px) {
          .top,
          .bottom {
            grid-template-columns: 1fr;
          }
        }
        .compact .top {
          grid-template-columns: minmax(160px, 200px) 1fr 1fr;
        }
        .card {
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 0.9rem 1rem 1rem;
          background: rgba(10, 16, 14, 0.55);
        }
        .gauge-card {
          border-color: ${color}55;
          background: linear-gradient(160deg, ${color}18, rgba(10, 16, 14, 0.65));
        }
        h3 {
          margin: 0 0 0.65rem;
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--ink-muted, #9ab0a4);
          font-weight: 600;
        }
        .who {
          margin: 0.35rem 0 0;
          font-size: 0.85rem;
          font-weight: 600;
          text-align: center;
        }
        .rec {
          margin: 0.45rem 0 0;
          font-size: 0.78rem;
          color: var(--ink-muted, #9ab0a4);
          line-height: 1.35;
        }
        .empty {
          color: var(--ink-muted, #9ab0a4);
          font-size: 0.85rem;
        }
        .corpus-grid {
          display: grid;
          grid-template-columns: repeat(6, minmax(0, 1fr));
          gap: 0.65rem;
          align-items: end;
        }
        @media (max-width: 700px) {
          .corpus-grid {
            grid-template-columns: repeat(3, 1fr);
          }
        }
        .corp {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          gap: 0.2rem;
        }
        .col {
          width: 100%;
          height: 76px;
          display: flex;
          align-items: flex-end;
          justify-content: center;
        }
        .stem {
          width: 70%;
          max-width: 36px;
          border-radius: 6px 6px 2px 2px;
          background: linear-gradient(180deg, #7eb892, #2a5a42);
          transition: height 0.5s ease;
        }
        .corp strong {
          font-size: 0.85rem;
        }
        .corp span {
          font-size: 0.65rem;
          color: var(--ink, #e8f2ec);
          line-height: 1.2;
        }
        .corp small {
          font-size: 0.58rem;
          color: var(--ink-muted, #9ab0a4);
        }
        .checks {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }
        .checks li {
          font-size: 0.78rem;
          display: flex;
          gap: 0.5rem;
          align-items: baseline;
        }
        .checks span {
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          padding: 0.12rem 0.35rem;
          border-radius: 4px;
          background: rgba(255, 255, 255, 0.06);
        }
        .checks .ok span {
          color: #5fd49a;
        }
        .checks .no span {
          color: #d45f5f;
        }
      `}</style>
    </section>
  );
}
