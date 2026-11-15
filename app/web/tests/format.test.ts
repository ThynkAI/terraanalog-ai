import { describe, expect, it } from "vitest";
import { buildQuery } from "@/lib/api";
import { fmtLat, fmtLonEarth, fmtLonEast, paramToWeights, parseLatLon, scoreColor, toCSV, weightsToParam } from "@/lib/format";

describe("geographic search parsing", () => {
  it("parses decimal lat,lon", () => {
    expect(parseLatLon("75.4, -89.7")).toEqual({ lat: 75.4, lon: -89.7 });
    expect(parseLatLon("-77.5 162.9")).toEqual({ lat: -77.5, lon: 162.9 });
  });
  it("parses hemisphere letters", () => {
    expect(parseLatLon("24.08S, 69.92W")).toEqual({ lat: -24.08, lon: -69.92 });
  });
  it("rejects names and out-of-range values", () => {
    expect(parseLatLon("Iceland")).toBeNull();
    expect(parseLatLon("95, 10")).toBeNull();
    expect(parseLatLon("10, 190")).toBeNull();
  });
});

describe("coordinate formatting", () => {
  it("Earth uses N/S and E/W", () => {
    expect(fmtLat(-77.5)).toBe("77.50°S");
    expect(fmtLonEarth(-89.68)).toBe("89.68°W");
  });
  it("planetary longitudes are always east-positive", () => {
    expect(fmtLonEast(-120.09)).toBe("-120.09°E");
  });
});

describe("weights deep-link round trip", () => {
  it("drops neutral weights and round-trips", () => {
    const p = weightsToParam({ terrain: 1, geology: 1.5, illumination: 0 });
    expect(p).toBe("geology:1.5,illumination:0");
    expect(paramToWeights(p)).toEqual({ geology: 1.5, illumination: 0 });
  });
  it("ignores invalid entries", () => {
    expect(paramToWeights("geology:abc,terrain:9,ok:2")).toEqual({ ok: 2 });
  });
});

describe("CSV export", () => {
  it("escapes and adds the synthetic banner", () => {
    const csv = toCSV([{ a: 'x,"y"', b: null }], "SYNTHETIC");
    expect(csv.split("\n")[0]).toBe("# SYNTHETIC");
    expect(csv).toContain('"x,""y"""');
  });
  it("handles empty input", () => {
    expect(toCSV([])).toBe("");
  });
});

describe("misc", () => {
  it("buildQuery skips empty values", () => {
    expect(buildQuery({ a: 1, b: "", c: undefined, d: null, e: false })).toBe("?a=1&e=false");
  });
  it("score colours: missing score is neutral grey", () => {
    expect(scoreColor(null)).toBe("#6c7587");
    expect(scoreColor(90)).not.toBe(scoreColor(20));
  });
});
