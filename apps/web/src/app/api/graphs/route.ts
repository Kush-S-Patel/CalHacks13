import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

const AGENT = process.env.NEXT_PUBLIC_AGENT_API ?? "http://127.0.0.1:8765";

/** Same-origin graphs proxy — never 404s; falls back to seed JSON. */
export async function GET() {
  try {
    const res = await fetch(`${AGENT}/v1/graphs`, { cache: "no-store" });
    if (res.ok) {
      return NextResponse.json(await res.json());
    }
  } catch {
    // fall through to seed
  }

  try {
    const file = path.join(process.cwd(), "public", "graphs.json");
    const raw = await readFile(file, "utf8");
    return NextResponse.json(JSON.parse(raw));
  } catch {
    return NextResponse.json({ detail: "graphs unavailable" }, { status: 503 });
  }
}