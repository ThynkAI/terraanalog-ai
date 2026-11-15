"use client";
import { useCallback, useEffect, useRef, useState } from "react";

export type Params = Record<string, string | number | boolean | null | undefined>;

export function buildQuery(params?: Params): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parse(res: Response) {
  const ct = res.headers.get("content-type") || "";
  const body = ct.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = typeof body === "object" && body && "detail" in body ? (body as { detail: unknown }).detail : body;
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

/** Retry only transient GET failures while a sleeping research service wakes. */
export async function apiGet<T>(path: string, params?: Params, signal?: AbortSignal): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    try {
      const res = await fetch(`/api${path}${buildQuery(params)}`, { signal, headers: { accept: "application/json" } });
      return await parse(res) as T;
    } catch (error) {
      if (signal?.aborted || (error as Error).name === "AbortError") throw error;
      const transient = error instanceof ApiError ? [502, 503, 504].includes(error.status) : error instanceof TypeError;
      if (!transient || attempt >= 2) throw error;
      await new Promise<void>((resolve, reject) => {
        const onAbort = () => { clearTimeout(timer); reject(signal?.reason ?? new DOMException("Aborted", "AbortError")); };
        const timer = setTimeout(() => { signal?.removeEventListener("abort", onAbort); resolve(); }, 1500 * (attempt + 1));
        signal?.addEventListener("abort", onAbort, { once: true });
      });
    }
  }
}

export async function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`/api${path}`, { method: "POST", body: JSON.stringify(body), signal, headers: { "content-type": "application/json" } });
  return parse(res) as Promise<T>;
}

/** Tiny data hook with abort-on-change and optional debounce. Pass path=null to skip. */
export function useApi<T>(path: string | null, params?: Params, debounceMs = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);
  const key = path ? path + buildQuery(params) : null;
  const latest = useRef(0);
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  // Tie displayed results to their request, so a new reference cannot show an old ranking.
  const [resultKey, setResultKey] = useState<string | null>(null);

  useEffect(() => {
    if (!key || !path) {
      setLoading(false);
      return;
    }
    const ctrl = new AbortController();
    const id = ++latest.current;
    setError(null);
    setLoading(true);
    const t = setTimeout(() => {
      apiGet<T>(path, params, ctrl.signal)
        .then((d) => {
          if (id === latest.current) {
            setResultKey(key);
            setData(d);
            setError(null);
          }
        })
        .catch((e: unknown) => {
          if ((e as Error).name === "AbortError") return;
          if (id === latest.current) setError((e as Error).message || "Request failed");
        })
        .finally(() => {
          if (id === latest.current) setLoading(false);
        });
    }, debounceMs);
    return () => {
      clearTimeout(t);
      ++latest.current;
      ctrl.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, debounceMs, attempt]);

  return { data: resultKey === key ? data : null, error, loading: loading || (!!key && resultKey !== key && !error), retry };
}
