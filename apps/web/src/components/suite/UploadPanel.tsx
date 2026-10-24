"use client";

import { useState } from "react";
import { erpApi } from "@/lib/erp-api";

const KINDS = [
  { value: "", label: "Auto-detect" },
  { value: "chart_of_accounts", label: "Chart of accounts" },
  { value: "revenue", label: "Revenue" },
  { value: "ap_aging", label: "AP aging" },
  { value: "ar_aging", label: "AR aging" },
  { value: "supply_chain", label: "Supply chain" },
  { value: "bank", label: "Bank" },
  { value: "scanned_financial", label: "Scanned financial" },
];

export function UploadPanel() {
  const [kind, setKind] = useState("");
  const [scanText, setScanText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onScan() {
    if (!scanText.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await erpApi.scanText(scanText);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "scan failed");
    } finally {
      setBusy(false);
    }
  }

  async function seed() {
    setBusy(true);
    setError(null);
    try {
      await erpApi.seedSamples();
      setResult({ ok: true, note: "Sample ERP workbooks loaded into the vault" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "seed failed");
    } finally {
      setBusy(false);
    }
  }

  async function trainBatch() {
    setBusy(true);
    setError(null);
    try {
      const res = await erpApi.trainBatch(3, 3);
      setResult({
        ok: true,
        note: `Indexed ${res.ocr_ingested} FinDoc OCR pages + FinCriticalED filings into the vault`,
        train: res,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "train intake failed");
    } finally {
      setBusy(false);
    }
  }

  async function docileBatch() {
    setBusy(true);
    setError(null);
    try {
      const res = await erpApi.ingestDocile(50);
      setResult({
        ok: res.ok,
        note: res.ok
          ? `DocILE: ${res.ingested} invoices → ${res.businesses_touched} enterprises (customers + supply links)`
          : res.error || "DocILE ingest failed",
        docile: res,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "docile intake failed");
    } finally {
      setBusy(false);
    }
  }

  async function onFile(file: File | null) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      if (file.name.toLowerCase().endsWith(".json")) {
        const text = await file.text();
        const parsed = JSON.parse(text) as { field_extractions?: unknown; word?: unknown };
        // DocILE annotation vs FinDoc OCR token list
        if (parsed.field_extractions) {
          const res = await erpApi.ingestDocileFile(new File([text], file.name, { type: "application/json" }));
          setResult(res);
        } else {
          const res = await erpApi.ingestOcr(file);
          setResult(res);
        }
      } else {
        const res = await erpApi.upload(file, kind || undefined, scanText || undefined);
        setResult(res);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "upload failed");
    } finally {
      setBusy(false);
    }
  }

  const analysis = result?.analysis as
    | { kind?: string; notes?: string[]; preview_rows?: Record<string, unknown>[]; row_count?: number }
    | undefined;
  const classification = result?.classification as
    | { doc_class?: string; confidence?: number; erp_kind?: string }
    | undefined;
  const extraction = result?.extraction as
    | { indexed_accounts?: number; line_count?: number }
    | undefined;
  const doc = result?.document as { filename?: string; status?: string; summary?: string } | undefined;
  const train = result?.train as { ocr_ingested?: number; totals?: Record<string, number> } | undefined;

  return (
    <section className="up">
      <header>
        <h1>Document intake</h1>
        <p>
          Spreadsheets, FinDoc OCR, FinCriticalED, and DocILE invoices land in the vault.
          DocILE expands each issuing vendor into a per-business profile (customers, supply
          parties, relationships) under Enterprises.
        </p>
      </header>

      <div className="cards">
        <div className="card">
          <h2>Upload workbook</h2>
          <label>
            Document type
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              {KINDS.map((k) => (
                <option key={k.value || "auto"} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
          </label>
          <label className="file">
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.txt,.json,.pdf,.png,.jpg,.jpeg"
              disabled={busy}
              onChange={(e) => void onFile(e.target.files?.[0] ?? null)}
            />
            <span>{busy ? "Analyzing…" : "Drop CSV / XLSX / FinDoc OCR JSON / scan"}</span>
          </label>
          <button type="button" className="ghost" disabled={busy} onClick={() => void seed()}>
            Load sample ERP pack
          </button>
          <button type="button" className="ghost" disabled={busy} onClick={() => void trainBatch()}>
            Index train_data (FinDoc + FinCriticalED)
          </button>
          <button type="button" className="ghost" disabled={busy} onClick={() => void docileBatch()}>
            Ingest DocILE → per-business knowledge
          </button>
          <p className="hint">
            Uses local mirrors of{" "}
            <a href="https://huggingface.co/datasets/daitavan/financial-documents">financial-documents</a>{" "}
            OCR +{" "}
            <a href="https://huggingface.co/datasets/TheFinAI/FinCriticalED">FinCriticalED</a>{" "}
            under <code>data/train_data</code>.
          </p>
        </div>

        <div className="card">
          <h2>Scanned financials</h2>
          <p className="hint">Paste OCR text from a phone scan or bank PDF extract.</p>
          <textarea
            value={scanText}
            onChange={(e) => setScanText(e.target.value)}
            placeholder={"1000  Operating Cash  18400\n1100  Accounts Receivable  27650\n..."}
            rows={8}
          />
          <button type="button" disabled={busy || !scanText.trim()} onClick={() => void onScan()}>
            Analyze scan text
          </button>
        </div>
      </div>

      {error && <p className="err">{error}</p>}

      {result && (
        <div className="out">
          <h2>Indexed</h2>
          {doc && (
            <p>
              <strong>{doc.filename}</strong> · {doc.status} — {doc.summary}
            </p>
          )}
          {classification && (
            <p className="meta">
              Classified as <strong>{classification.doc_class}</strong> → ERP{" "}
              <strong>{classification.erp_kind}</strong> · confidence{" "}
              {classification.confidence ?? "—"}
              {extraction
                ? ` · ${extraction.indexed_accounts ?? 0} GL lines from ${extraction.line_count ?? 0} OCR amounts`
                : ""}
            </p>
          )}
          {train && (
            <p className="meta">
              Train batch: {train.ocr_ingested ?? 0} OCR pages · vault accounts{" "}
              {train.totals?.accounts ?? "—"} · parties {train.totals?.parties ?? "—"}
            </p>
          )}
          {typeof result?.note === "string" && <p className="meta">{result.note}</p>}
          {analysis && (
            <>
              <p className="meta">
                Detected <strong>{analysis.kind}</strong> · {analysis.row_count ?? 0} rows ·{" "}
                {(analysis.notes || []).join(" · ")}
              </p>
              {analysis.preview_rows && analysis.preview_rows.length > 0 && (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {Object.keys(analysis.preview_rows[0]).map((h) => (
                          <th key={h}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.preview_rows.map((row, i) => (
                        <tr key={i}>
                          {Object.values(row).map((v, j) => (
                            <td key={j}>{String(v ?? "")}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
          <p className="next">
            Open <a href="/suite">Summary</a> or <a href="/suite/graphs">Graphs</a> — the enterprise
            map updates from this vault.
          </p>
        </div>
      )}

      <style jsx>{`
        .up {
          padding: 1.5rem 2rem 3rem;
        }
        h1 {
          font-family: var(--font-display);
          font-size: clamp(1.7rem, 3.5vw, 2.2rem);
          margin: 0 0 0.35rem;
        }
        header p {
          margin: 0 0 1.25rem;
          color: var(--ink-muted);
          max-width: 40rem;
        }
        .cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 0.85rem;
        }
        .card {
          padding: 1.2rem;
          border: 1px solid var(--line);
          border-radius: 14px;
          background: rgba(26, 42, 34, 0.5);
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }
        h2 {
          font-family: var(--font-display);
          font-size: 1.1rem;
          margin: 0;
        }
        label {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
          font-size: 0.8rem;
          color: var(--ink-muted);
        }
        select,
        textarea {
          background: var(--bg-deep);
          border: 1px solid var(--line);
          color: var(--ink);
          border-radius: 8px;
          padding: 0.55rem 0.7rem;
          font: inherit;
        }
        .file {
          border: 1px dashed var(--accent);
          border-radius: 10px;
          padding: 1.4rem;
          text-align: center;
          cursor: pointer;
          color: var(--ink);
        }
        .file input {
          display: none;
        }
        button {
          border: none;
          background: var(--accent);
          color: #04140c;
          font-weight: 700;
          padding: 0.7rem 1rem;
          border-radius: 8px;
        }
        button:disabled {
          opacity: 0.5;
        }
        button.ghost {
          background: transparent;
          border: 1px solid var(--line);
          color: var(--ink-muted);
        }
        .hint {
          margin: 0;
          font-size: 0.82rem;
          color: var(--ink-muted);
        }
        .hint :global(a) {
          color: var(--accent-bright);
        }
        .hint :global(code) {
          font-size: 0.75rem;
        }
        .err {
          color: var(--danger);
          margin-top: 1rem;
        }
        .out {
          margin-top: 1.25rem;
          padding: 1.1rem 1.2rem;
          border: 1px solid var(--line);
          border-radius: 12px;
        }
        .meta {
          color: var(--ink-muted);
          font-size: 0.88rem;
        }
        .table-wrap {
          overflow: auto;
          margin-top: 0.75rem;
        }
        table {
          border-collapse: collapse;
          width: 100%;
          font-size: 0.78rem;
        }
        th,
        td {
          border-bottom: 1px solid var(--line);
          padding: 0.35rem 0.5rem;
          text-align: left;
          white-space: nowrap;
        }
        th {
          color: var(--ink-muted);
          font-weight: 600;
        }
        .next {
          margin: 0.85rem 0 0;
          font-size: 0.88rem;
        }
        .next a {
          color: var(--accent-bright);
        }
      `}</style>
    </section>
  );
}