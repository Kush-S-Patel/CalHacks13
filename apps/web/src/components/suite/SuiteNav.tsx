"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NessieBadge } from "@/components/NessieBadge";

const LINKS = [
  { href: "/suite", label: "Summary" },
  { href: "/suite/claims", label: "Claims" },
  { href: "/suite/jobs", label: "Jobs" },
  { href: "/suite/upload", label: "Upload" },
  { href: "/suite/documents", label: "Documents" },
  { href: "/suite/businesses", label: "Enterprises" },
  { href: "/suite/graphs", label: "Graphs" },
  { href: "/suite/work", label: "Work" },
  { href: "/", label: "World" },
];

export function SuiteNav() {
  const path = usePathname();
  return (
    <nav className="snav">
      <Link href="/suite" className="brand">
        SwarmCFO <span>ERP Suite</span>
      </Link>
      <div className="links">
        {LINKS.map((l) => (
          <Link key={l.href} href={l.href} className={path === l.href ? "on" : ""}>
            {l.label}
          </Link>
        ))}
        <NessieBadge compact />
      </div>
      <style jsx>{`
        .snav {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          padding: 1rem 2rem;
          border-bottom: 1px solid var(--line);
          background: rgba(12, 18, 16, 0.55);
          position: sticky;
          top: 0;
          z-index: 20;
          backdrop-filter: blur(10px);
        }
        .snav :global(.brand) {
          font-family: var(--font-display);
          font-weight: 700;
          font-size: 1.15rem;
        }
        .snav :global(.brand span) {
          color: var(--ink-muted);
          font-weight: 500;
          font-size: 0.85rem;
          margin-left: 0.35rem;
        }
        .links {
          display: flex;
          flex-wrap: wrap;
          gap: 0.35rem;
        }
        .snav :global(a) {
          font-size: 0.82rem;
          font-weight: 600;
          padding: 0.4rem 0.75rem;
          border-radius: 8px;
          color: var(--ink-muted);
        }
        .snav :global(a.on),
        .snav :global(a:hover) {
          color: var(--ink);
          background: #1f3328;
        }
      `}</style>
    </nav>
  );
}