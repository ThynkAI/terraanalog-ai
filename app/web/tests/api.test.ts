import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiGet, apiPost } from "@/lib/api";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("research-service recovery", () => {
  it("recovers after transient upstream failures", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockResolvedValueOnce(json({ detail: "waking" }, 502)).mockResolvedValueOnce(json({ detail: "waking" }, 503)).mockResolvedValueOnce(json({ sites: [] }));
    vi.stubGlobal("fetch", fetch);
    const result = apiGet("/sites");
    await vi.runAllTimersAsync();
    await expect(result).resolves.toEqual({ sites: [] });
    expect(fetch).toHaveBeenCalledTimes(3);
  });
  it("does not retry invalid scientific queries", async () => {
    const fetch = vi.fn().mockResolvedValue(json({ detail: "unknown reference" }, 422));
    vi.stubGlobal("fetch", fetch);
    await expect(apiGet("/rankings")).rejects.toMatchObject({ status: 422 });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("stops retrying when the user changes the request", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockResolvedValue(json({ detail: "waking" }, 504));
    vi.stubGlobal("fetch", fetch);
    const controller = new AbortController();
    const result = apiGet("/sites", {}, controller.signal);
    const assertion = expect(result).rejects.toMatchObject({ name: "AbortError" });
    await vi.advanceTimersByTimeAsync(1);
    controller.abort();
    await vi.runAllTimersAsync();
    await assertion;
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("bounds retries and preserves the final service error", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockImplementation(async () => json({ detail: "temporarily unavailable" }, 502));
    vi.stubGlobal("fetch", fetch);
    const assertion = expect(apiGet("/meta")).rejects.toBeInstanceOf(ApiError);
    await vi.runAllTimersAsync();
    await assertion;
    expect(fetch).toHaveBeenCalledTimes(3);
  });
  it("never automatically repeats POST requests", async () => {
    const fetch = vi.fn().mockResolvedValue(json({ detail: "unavailable" }, 503));
    vi.stubGlobal("fetch", fetch);
    await expect(apiPost("/recommend", { query: "Mars rover" })).rejects.toMatchObject({ status: 503 });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
