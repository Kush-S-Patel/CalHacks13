"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

type NessieSnap = {
  status?: string;
  used_nessie?: boolean;
  marker?: string;
  account_id?: string;
  account_number_last4?: string;
  tx_count?: number;
  last_sync?: string | null;
  brand?: string;
};

/** Visible Capital One Nessie marker — shows the bank rail was used. */
export function NessieBadge({ compact = false }: { compact?: boolean }) {
  const [data, setData] = useState<NessieSnap | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch(`${API}/v1/nessie`, { cache: "no-store" });
        if (!res.ok) return;
        const json = (await res.json()) as NessieSnap;
        if (!cancelled) setData(json);
      } catch {
        /* agent offline */
      }
    }
    void load();
    const t = setInterval(() => void load(), 8000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  const live = Boolean(data?.used_nessie && data.status === "connected");
  const synced = Boolean(data?.tx_count && data.tx_count > 0);

  return (
    <a
      className={`nessie ${compact ? "compact" : ""} ${live ? "live" : ""}`}
      href="https://api.nessieisreal.com/"
      target="_blank"
      rel="noreferrer"
      title={data?.marker || "Capital One Nessie Hackathon API"}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/nessie-mark.svg" alt="Capital One Nessie" width={compact ? 96 : 120} height={compact ? 32 : 40} />
      {!compact && (
        <span className="meta">
          <strong>{synced ? "Bank rail live" : live ? "Connected" : "Nessie"}</strong>
          <em>
            {synced
              ? `${data?.tx_count} txs · ****${data?.account_number_last4 || "····"}`
              : data?.marker || "Capital One Hackathon API"}
          </em>
        </span>
      )}
      <style jsx>{`
        .nessie {
          display: inline-flex;
          align-items: center;
          gap: 0.75rem;
          text-decoration: none;
          color: inherit;
          padding: 0.35rem 0.5rem;
          border-radius: 10px;
          border: 1px solid rgba(0, 114, 206, 0.35);
          background: rgba(0, 73, 119, 0.18);
          transition: border-color 0.2s ease, background 0.2s ease;
        }
        .nessie.live {
          border-color: rgba(0, 114, 206, 0.75);
          box-shadow: 0 0 0 1px rgba(0, 114, 206, 0.2);
        }
        .nessie:hover {
          background: rgba(0, 73, 119, 0.32);
        }
        .nessie :global(img) {
          display: block;
          height: auto;
        }
        .meta {
          display: flex;
          flex-direction: column;
          gap: 0.1rem;
          min-width: 0;
        }
        .meta strong {
          font-size: 0.78rem;
          font-weight: 700;
          color: #9fd0ff;
        }
        .meta em {
          font-style: normal;
          font-size: 0.68rem;
          color: var(--ink-muted);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 14rem;
        }
        .compact {
          padding: 0.2rem;
          border: none;
          background: transparent;
        }
      `}</style>
    </a>
  );
}
