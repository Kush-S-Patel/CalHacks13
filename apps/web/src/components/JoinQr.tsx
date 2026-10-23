"use client";

import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";

export function JoinQr() {
  const [url, setUrl] = useState("");

  useEffect(() => {
    setUrl(`${window.location.origin}/phone`);
  }, []);

  if (!url) return null;

  return (
    <aside className="qr">
      <p>Judges join</p>
      <QRCodeSVG value={url} size={112} bgColor="transparent" fgColor="#e8f0ea" />
      <span className="url">{url.replace(/^https?:\/\//, "")}</span>
      <style jsx>{`
        .qr {
          position: fixed;
          right: 1.25rem;
          bottom: 1.25rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.4rem;
          padding: 0.85rem;
          background: rgba(12, 18, 16, 0.85);
          border: 1px solid var(--line);
          border-radius: 12px;
          backdrop-filter: blur(8px);
        }
        p {
          margin: 0;
          font-size: 0.7rem;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--ink-muted);
        }
        .url {
          font-size: 0.65rem;
          color: var(--ink-muted);
          max-width: 120px;
          text-align: center;
          word-break: break-all;
        }
        @media (max-width: 720px) {
          .qr {
            display: none;
          }
        }
      `}</style>
    </aside>
  );
}