import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** Server-side proxy to the FastAPI data/scoring service. API_URL is read at request time (runtime-configurable in Docker). */
const API_URL = () => (process.env.API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
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
    return NextResponse.json({ detail: "Data service unavailable. Start the FastAPI backend (see README)." }, { status: 502 });
  }
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(req, (await ctx.params).path, "GET");
}
export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(req, (await ctx.params).path, "POST");
}
