import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  SERVICE_WAKE_MESSAGE,
  TRANSIENT_RETRY_DELAYS_MS,
  apiGet,
  apiPost,
  looksLikeHtml,
  userErrorMessage,
} from "@/lib/api";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
const html = (status = 502, title = String(status)) =>
  new Response(`<!DOCTYPE html><html lang="en"><head><title>${title}</title></head><body>Application failed to respond</body></html>`, {
    status,
    headers: { "content-type": "text/html; charset=utf-8" },
  });

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
    await expect(apiGet("/rankings")).rejects.toMatchObject({ status: 422, message: "unknown reference" });
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
  it("retries transient failures across the wake window and then stops", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockImplementation(async () => json({ detail: "temporarily unavailable" }, 502));
    vi.stubGlobal("fetch", fetch);
    const assertion = expect(apiGet("/meta")).rejects.toMatchObject({ status: 502, message: SERVICE_WAKE_MESSAGE });
    await vi.runAllTimersAsync();
    await assertion;
    expect(fetch).toHaveBeenCalledTimes(TRANSIENT_RETRY_DELAYS_MS.length + 1);
    expect(TRANSIENT_RETRY_DELAYS_MS.reduce((a, b) => a + b, 0)).toBeGreaterThanOrEqual(60_000);
    expect(TRANSIENT_RETRY_DELAYS_MS.reduce((a, b) => a + b, 0)).toBeLessThanOrEqual(90_000);
  });
  it("never automatically repeats POST requests", async () => {
    const fetch = vi.fn().mockResolvedValue(json({ detail: "unavailable" }, 503));
    vi.stubGlobal("fetch", fetch);
    await expect(apiPost("/recommend", { query: "Mars rover" })).rejects.toMatchObject({ status: 503, message: SERVICE_WAKE_MESSAGE });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});

describe("HTML gateway pages", () => {
  it("does not put a Render 502 HTML body in the error message", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockImplementation(async () => html(502));
    vi.stubGlobal("fetch", fetch);
    const pending = apiGet("/case-studies");
    const assertion = expect(pending).rejects.toBeInstanceOf(ApiError);
    await vi.runAllTimersAsync();
    const error = await pending.then(() => null, (e: unknown) => e as ApiError);
    await assertion;
    expect(error).toMatchObject({ status: 502, message: SERVICE_WAKE_MESSAGE });
    expect(error?.message).not.toMatch(/<!DOCTYPE|<title>502|Application failed to respond/i);
    expect(fetch).toHaveBeenCalledTimes(TRANSIENT_RETRY_DELAYS_MS.length + 1);
  });
  it("recovers when an HTML 502 is followed by a JSON payload", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockResolvedValueOnce(html(502)).mockResolvedValueOnce(html(503)).mockResolvedValueOnce(json({ cases: [] }));
    vi.stubGlobal("fetch", fetch);
    const result = apiGet("/case-studies");
    await vi.runAllTimersAsync();
    await expect(result).resolves.toEqual({ cases: [] });
    expect(fetch).toHaveBeenCalledTimes(3);
  });
  it("retries a network failure and maps it to the wake message", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetch);
    const pending = apiGet("/meta");
    const assertion = expect(pending).rejects.toBeInstanceOf(TypeError);
    await vi.runAllTimersAsync();
    const error = await pending.then(() => null, (e: unknown) => e);
    await assertion;
    expect(userErrorMessage(error)).toBe(SERVICE_WAKE_MESSAGE);
    expect(fetch).toHaveBeenCalledTimes(TRANSIENT_RETRY_DELAYS_MS.length + 1);
  });
  it("still surfaces JSON validation details from our API", async () => {
    const fetch = vi.fn().mockResolvedValue(json({ detail: "unknown reference" }, 400));
    vi.stubGlobal("fetch", fetch);
    await expect(apiGet("/rankings")).rejects.toMatchObject({ status: 400, message: "unknown reference" });
  });
});

describe("user-facing error text", () => {
  it("detects HTML error pages", () => {
    expect(looksLikeHtml("<!DOCTYPE html> <html lang=\"en\"> <head> <title>502</title>")).toBe(true);
    expect(looksLikeHtml("unknown reference")).toBe(false);
  });
  it("maps dumped HTML and network failures to the wake message", () => {
    const dumped = "<!DOCTYPE html> <html lang=\"en\"> <head> <title>502</title></head></html>";
    expect(userErrorMessage(new ApiError(502, dumped))).toBe(SERVICE_WAKE_MESSAGE);
    expect(userErrorMessage(new ApiError(502, dumped))).not.toMatch(/<!DOCTYPE|<html/i);
    expect(userErrorMessage(new ApiError(422, "unknown reference"))).toBe("unknown reference");
    expect(userErrorMessage(new TypeError("Failed to fetch"))).toBe(SERVICE_WAKE_MESSAGE);
  });
});
