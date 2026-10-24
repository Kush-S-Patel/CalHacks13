"use client";

import { useMemo, useState } from "react";
import type { GraphEdge, GraphNode, GraphPayload } from "@/lib/graph-types";
import { layoutForce, layoutHierarchical, type LaidOutNode } from "@/lib/forceLayout";

const KIND_FILL: Record<string, string> = {
  company: "#3d9b6a",
  cash: "#5fd49a",
  origin: "#6b8f71",
  processor: "#4a7c59",
  distributor: "#2f6b4f",
  packaging: "#8fa396",
  logistics: "#7a9e8a",
  site: "#c9a227",
  customer: "#4a90a4",
  vendor: "#2f6b4f",
  invoice: "#d45b5b",
  bank_txn: "#5b8fd4",
  bank: "#5b8fd4",
  bank_fp: "#3d5a80",
  receivable: "#e0a045",
  payment: "#c9a227",
  policy: "#9b7b3d",
  gl: "#8b7355",
  forecast: "#5fd49a",
};

function nodeFill(n: GraphNode): string {
  if (n.fraud) return "#d45b5b";
  if (n.held) return "#c9a227";
  return KIND_FILL[n.kind] ?? "#1a2a22";
}

function edgeStroke(e: GraphEdge): string {
  if (e.fraud) return "#d45b5b";
  if (e.held) return "#c9a227";
  if (e.kind === "revenue") return "#5fd49a";
  if (e.kind === "policy_link") return "#9b7b3d";
  return "rgba(232,240,234,0.35)";
}

type Props = {
  graph: GraphPayload;
  height?: number;
};

export function GraphCanvas({ graph, height = 420 }: Props) {
  const width = 960;
  const [hover, setHover] = useState<string | null>(null);
  const [selected, setSelected] = useState<LaidOutNode | GraphEdge | null>(null);

  const nodes = useMemo(() => {
    if (graph.layout === "hierarchical") {
      return layoutHierarchical(graph.nodes, width, height);
    }
    return layoutForce(graph.nodes, graph.edges, width, height);
  }, [graph, height]);

  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const tierLabels = useMemo(() => {
    if (graph.layout !== "hierarchical") return [];
    const map = new Map<number, string>();
    for (const n of graph.nodes) {
      if (n.tier != null && n.tier_label) map.set(n.tier, n.tier_label);
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0]);
  }, [graph]);

  return (
    <div className="gc">
      <header>
        <div>
          <h3>{graph.title}</h3>
          <p>{graph.subtitle}</p>
        </div>
        <div className="badges">
          <span>{graph.nodes.length} nodes</span>
          <span>{graph.edges.length} links</span>
          <span className="fraud">
            {graph.nodes.filter((n) => n.fraud).length + graph.edges.filter((e) => e.fraud).length} fraud
          </span>
        </div>
      </header>

      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={graph.title}>
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="rgba(232,240,234,0.45)" />
          </marker>
          <marker id="arrow-fraud" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#d45b5b" />
          </marker>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2.5" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {graph.layout === "hierarchical" &&
          tierLabels.map(([tier, label], i) => {
            const y =
              36 +
              (tierLabels.length <= 1
                ? height / 2
                : (i / (tierLabels.length - 1)) * (height - 72));
            return (
              <text key={tier} x={12} y={y + 4} className="tier">
                {label}
              </text>
            );
          })}

        {graph.edges.map((e) => {
          const a = byId.get(e.source);
          const b = byId.get(e.target);
          if (!a || !b) return null;
          const midX = (a.x + b.x) / 2;
          const midY = (a.y + b.y) / 2;
          const active = hover === e.id || hover === e.source || hover === e.target;
          return (
            <g
              key={e.id}
              className={`edge ${e.fraud ? "fraud" : ""} ${e.held ? "held" : ""}`}
              opacity={hover && !active ? 0.2 : 1}
              onMouseEnter={() => setHover(e.id)}
              onMouseLeave={() => setHover(null)}
              onClick={() => setSelected(e)}
              style={{ cursor: "pointer" }}
            >
              <line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={edgeStroke(e)}
                strokeWidth={e.fraud || e.held ? 2.4 : 1.2}
                strokeDasharray={e.fraud ? "6 4" : e.held ? "3 3" : undefined}
                markerEnd={e.fraud ? "url(#arrow-fraud)" : "url(#arrow)"}
              />
              <rect
                x={midX - 36}
                y={midY - 9}
                width={72}
                height={16}
                rx={3}
                fill="rgba(12,18,16,0.85)"
                stroke={e.fraud ? "#d45b5b" : "transparent"}
              />
              <text x={midX} y={midY + 3} textAnchor="middle" className="elabel">
                {e.fraud ? `FRAUD ${e.amount_label}` : e.amount_label || e.label}
              </text>
            </g>
          );
        })}

        {nodes.map((n) => {
          const r = n.kind === "company" || n.kind === "cash" ? 22 : n.fraud ? 18 : 14;
          const active = hover === n.id;
          return (
            <g
              key={n.id}
              transform={`translate(${n.x},${n.y})`}
              opacity={hover && !active && hover !== n.id ? 0.35 : 1}
              onMouseEnter={() => setHover(n.id)}
              onMouseLeave={() => setHover(null)}
              onClick={() => setSelected(n)}
              style={{ cursor: "pointer" }}
              filter={n.fraud ? "url(#glow)" : undefined}
            >
              <circle
                r={r}
                fill={nodeFill(n)}
                stroke={n.fraud ? "#ff8a8a" : n.held ? "#e0c35a" : "rgba(232,240,234,0.25)"}
                strokeWidth={n.fraud || n.held ? 2.5 : 1}
              />
              {n.fraud && (
                <text y={4} textAnchor="middle" className="fraudmark">
                  !
                </text>
              )}
              <text y={r + 12} textAnchor="middle" className="nlabel">
                {n.label.length > 22 ? `${n.label.slice(0, 20)}…` : n.label}
              </text>
              <text y={r + 24} textAnchor="middle" className="namt">
                {n.amount_label}
              </text>
            </g>
          );
        })}
      </svg>

      {selected && (
        <aside className="detail">
          {"source" in selected ? (
            <>
              <strong>{selected.fraud ? "FRAUD LINK" : selected.held ? "HELD" : "Flow"}</strong>
              <p>
                {selected.source} → {selected.target}
              </p>
              <p className="mono">{selected.amount_label}</p>
              <p className="muted">{selected.kind}{selected.policy_id ? ` · ${selected.policy_id}` : ""}</p>
            </>
          ) : (
            <>
              <strong>{selected.fraud ? "FRAUD NODE" : selected.label}</strong>
              <p className="mono">{selected.amount_label}</p>
              <p className="muted">
                {selected.kind}
                {selected.tier_label ? ` · ${selected.tier_label}` : ""}
              </p>
            </>
          )}
          <button type="button" onClick={() => setSelected(null)}>
            Close
          </button>
        </aside>
      )}

      <style jsx>{`
        .gc {
          position: relative;
          border: 1px solid var(--line);
          border-radius: 14px;
          background:
            radial-gradient(ellipse 70% 50% at 50% 0%, rgba(61, 155, 106, 0.12), transparent),
            rgba(12, 18, 16, 0.65);
          overflow: hidden;
        }
        header {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          padding: 1rem 1.15rem 0.35rem;
          align-items: flex-start;
        }
        h3 {
          font-family: var(--font-display);
          margin: 0;
          font-size: 1.15rem;
        }
        header p {
          margin: 0.2rem 0 0;
          color: var(--ink-muted);
          font-size: 0.82rem;
        }
        .badges {
          display: flex;
          gap: 0.4rem;
          flex-wrap: wrap;
        }
        .badges span {
          font-size: 0.68rem;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          background: var(--bg-deep);
          color: var(--ink-muted);
        }
        .badges .fraud {
          color: #ff8a8a;
        }
        svg {
          width: 100%;
          height: auto;
          display: block;
        }
        :global(.tier) {
          fill: rgba(143, 163, 150, 0.7);
          font-size: 10px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }
        :global(.elabel) {
          fill: #e8f0ea;
          font-size: 9px;
          font-variant-numeric: tabular-nums;
        }
        :global(.nlabel) {
          fill: #e8f0ea;
          font-size: 10px;
          font-weight: 600;
        }
        :global(.namt) {
          fill: #8fa396;
          font-size: 9px;
          font-variant-numeric: tabular-nums;
        }
        :global(.fraudmark) {
          fill: #fff;
          font-size: 14px;
          font-weight: 800;
        }
        .detail {
          position: absolute;
          right: 0.85rem;
          bottom: 0.85rem;
          min-width: 180px;
          max-width: 240px;
          padding: 0.85rem 1rem;
          background: rgba(12, 18, 16, 0.92);
          border: 1px solid var(--line);
          border-radius: 10px;
          backdrop-filter: blur(8px);
        }
        .detail strong {
          font-size: 0.85rem;
        }
        .detail p {
          margin: 0.3rem 0 0;
          font-size: 0.82rem;
        }
        .detail .muted {
          color: var(--ink-muted);
        }
        .detail button {
          margin-top: 0.55rem;
          background: transparent;
          border: 1px solid var(--line);
          color: var(--ink-muted);
          border-radius: 4px;
          padding: 0.25rem 0.5rem;
          font-size: 0.72rem;
        }
      `}</style>
    </div>
  );
}