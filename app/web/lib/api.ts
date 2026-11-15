"use client";
import { useCallback, useEffect, useRef, useState } from "react";

export type Params = Record<string, string | number | boolean | null | undefined>;

/** Backoff between transient GET retries while a sleeping research service wakes (~70s of waits). */
export const TRANSIENT_RETRY_DELAYS_MS = [2000, 4000, 8000, 16000, 20000, 20000] as const;

export const SERVICE_WAKE_MESSAGE =
  "The research service is starting up — this can take up to a minute. Retrying…";

const TRANSIENT_STATUS = new Set([502, 503, 504]);

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

export function isTransientStatus(status: number): boolean {
  return TRANSIENT_STATUS.has(status);
}

/** True when a response body is an HTML error page (for example Render's 502 wake page). */
export function looksLikeHtml(text: string): boolean {
  const head = text.trimStart().slice(0, 240).toLowerCase();
  return (
    head.startsWith("<!doctype") ||
    head.startsWith("<html") ||
    head.includes("<title>502") ||
    head.includes("<title>503") ||
    head.includes("<title>504")
  );
}

function isJsonContentType(ct: string): boolean {
  const t = ct.toLowerCase();
  return t.includes("application/json") || t.includes("+json");
}

function messageFromDetail(status: number, raw: unknown): string {
  if (isTransientStatus(status)) return SERVICE_WAKE_MESSAGE;
  if (typeof raw === "string") {
    if (looksLikeHtml(raw) || raw.trimStart().startsWith("<")) {
      return "The research service returned an unexpected error. Please retry.";
    }
    return raw || "Request failed";
  }
  if (raw && typeof raw === "object") {
    try {
      return JSON.stringify(raw);
    } catch {
      return "Request failed";
    }
  }
  return "Request failed";
}

/** Map any thrown API/network error to a short message safe to render in the UI. */
export function userErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (isTransientStatus(error.status) || looksLikeHtml(error.message)) return SERVICE_WAKE_MESSAGE;
    return error.message || "Request failed";
  }
  if (error instanceof TypeError) return SERVICE_WAKE_MESSAGE;
  if (error instanceof Error) {
    if (looksLikeHtml(error.message) || /failed to fetch|networkerror|load failed|network request failed/i.test(error.message)) {
      return SERVICE_WAKE_MESSAGE;
    }
    return error.message || "Request failed";
  }
  return "Request failed";
}

async function wait(ms: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) throw signal.reason ?? new DOMException("Aborted", "AbortError");
  await new Promise<void>((resolve, reject) => {
    const onAbort = () => {
      clearTimeout(timer);
      reject(signal?.reason ?? new DOMException("Aborted", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

async function parse(res: Response) {
  const ct = res.headers.get("content-type") || "";
  const json = isJsonContentType(ct);
  let body: unknown;
  if (json) {
    try {
      body = await res.json();
    } catch {
      body = null;
    }
  } else {
    body = await res.text();
  }
  if (!res.ok) {
    const detail = json && body && typeof body === "object" && "detail" in body
      ? (body as { detail: unknown }).detail
      : body;
    throw new ApiError(res.status, messageFromDetail(res.status, detail));
  }
  return body;
}

function isTransientError(error: unknown): boolean {
  if (error instanceof ApiError) return isTransientStatus(error.status);
  return error instanceof TypeError;
}

/** Retry only transient GET failures while a sleeping research service wakes. */
export async function apiGet<T>(path: string, params?: Params, signal?: AbortSignal): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    try {
      const res = await fetch(`/api${path}${buildQuery(params)}`, { signal, headers: { accept: "application/json" } });
      return await parse(res) as T;
    } catch (error) {
      if (signal?.aborted || (error as Error).name === "AbortError") throw error;
      const delay = TRANSIENT_RETRY_DELAYS_MS[attempt];
      if (!isTransientError(error) || delay === undefined) throw error;
      await wait(delay, signal);
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
          if (id === latest.current) setError(userErrorMessage(e));
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
