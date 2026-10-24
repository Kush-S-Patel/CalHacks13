import type { GraphEdge, GraphNode } from "./graph-types";

export type LaidOutNode = GraphNode & { x: number; y: number; vx: number; vy: number };

/** Tiny force simulation — no d3 dependency, stable enough for demo graphs. */
export function layoutForce(
  nodes: GraphNode[],
  edges: GraphEdge[],
  width: number,
  height: number,
  ticks = 180,
): LaidOutNode[] {
  const cx = width / 2;
  const cy = height / 2;
  const laid: LaidOutNode[] = nodes.map((n, i) => {
    const a = (i / Math.max(nodes.length, 1)) * Math.PI * 2;
    const r = 40 + (i % 5) * 28;
    return { ...n, x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r, vx: 0, vy: 0 };
  });
  const byId = new Map(laid.map((n) => [n.id, n]));

  for (let t = 0; t < ticks; t++) {
    const alpha = 1 - t / ticks;

    // repulsion
    for (let i = 0; i < laid.length; i++) {
      for (let j = i + 1; j < laid.length; j++) {
        const a = laid[i];
        const b = laid[j];
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let dist = Math.hypot(dx, dy) || 0.01;
        const force = (2200 * alpha) / (dist * dist);
        dx = (dx / dist) * force;
        dy = (dy / dist) * force;
        a.vx -= dx;
        a.vy -= dy;
        b.vx += dx;
        b.vy += dy;
      }
    }

    // springs
    for (const e of edges) {
      const a = byId.get(e.source);
      const b = byId.get(e.target);
      if (!a || !b) continue;
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      const dist = Math.hypot(dx, dy) || 0.01;
      const ideal = e.fraud || e.held ? 130 : 100;
      const force = ((dist - ideal) * 0.06) * alpha;
      dx = (dx / dist) * force;
      dy = (dy / dist) * force;
      a.vx += dx;
      a.vy += dy;
      b.vx -= dx;
      b.vy -= dy;
    }

    // center gravity + fraud pull slightly outward
    for (const n of laid) {
      n.vx += (cx - n.x) * 0.012 * alpha;
      n.vy += (cy - n.y) * 0.012 * alpha;
      if (n.kind === "company" || n.kind === "cash") {
        n.vx += (cx - n.x) * 0.04;
        n.vy += (cy - n.y) * 0.04;
      }
      n.vx *= 0.75;
      n.vy *= 0.75;
      n.x += n.vx;
      n.y += n.vy;
      n.x = Math.min(width - 40, Math.max(40, n.x));
      n.y = Math.min(height - 28, Math.max(28, n.y));
    }
  }

  return laid;
}

export function layoutHierarchical(
  nodes: GraphNode[],
  width: number,
  height: number,
): LaidOutNode[] {
  const tiers = new Map<number, GraphNode[]>();
  for (const n of nodes) {
    const t = n.tier ?? 0;
    if (!tiers.has(t)) tiers.set(t, []);
    tiers.get(t)!.push(n);
  }
  const tierKeys = [...tiers.keys()].sort((a, b) => a - b);
  const padX = 56;
  const padY = 36;
  const usableW = width - padX * 2;
  const usableH = height - padY * 2;

  const laid: LaidOutNode[] = [];
  tierKeys.forEach((tier, ti) => {
    const row = tiers.get(tier)!;
    const y = padY + (tierKeys.length <= 1 ? usableH / 2 : (ti / (tierKeys.length - 1)) * usableH);
    row.forEach((n, ni) => {
      const x =
        padX + (row.length <= 1 ? usableW / 2 : (ni / (row.length - 1)) * usableW);
      laid.push({ ...n, x, y, vx: 0, vy: 0 });
    });
  });
  return laid;
}