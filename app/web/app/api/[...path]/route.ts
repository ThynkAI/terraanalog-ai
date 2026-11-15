import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Server-side proxy to the FastAPI data/scoring service, resolved at request time (runtime-configurable in Docker / Render).
 * API_URL (full URL) wins; otherwise API_HOST is used — a public hostname ("x.onrender.com" → https) or a private "host:port" (→ http).
 */
const API_URL = () => {
  if (process.env.API_URL) return process.env.API_URL.replace(/\/$/, "");
  const host = process.env.API_HOST;
  if (host) return (/:\d+$/.test(host) ? `http://${host}` : `https://${host}`).replace(/\/$/, "");
  return "http://127.0.0.1:8000";
};
const SAFE_SEGMENT = /^[A-Za-z0-9_.\-]+$/;

async function forward(req: NextRequest, path: string[], method: "GET" | "POST") {
  if (!path.every((p) => SAFE_SEGMENT.test(p) && p !== ".." && p !== ".")) {
    return NextResponse.json({ detail: "invalid path" }, { status: 400 });
  }
  const target = `${API_URL()}/api/${path.join("/")}${req.nextUrl.search}`;
  try {
    const res = await fetch(target, {
      method,
      headers: { "content-type": req.headers.get("content-type") || "application/json", accept: req.headers.get("accept") || "*/*" },
      body: method === "POST" ? await req.text() : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
    });
    const headers = new Headers();
    for (const h of ["content-type", "content-disposition"]) {
      const v = res.headers.get(h);
      if (v) headers.set(h, v);
    }
    headers.set("cache-control", "no-store");
    return new NextResponse(await res.arrayBuffer(), { status: res.status, headers });
  } catch {
    return NextResponse.json({ detail: "The research service is temporarily unavailable or waking from inactivity. Please retry shortly." }, { status: 502 });
  }
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(req, (await ctx.params).path, "GET");
}
export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(req, (await ctx.params).path, "POST");
}
