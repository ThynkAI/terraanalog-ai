"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useApi } from "@/lib/api";
import { fmtLat, fmtLonEast, pct } from "@/lib/format";
import { useUrlState } from "@/lib/useUrlState";
import type { Body, PlanetaryReference, ScoreResult } from "@/lib/types";
import { useMeta, useCriteriaLabels } from "./MetaContext";
import { PlanetViewer } from "./PlanetViewer";
import { ObjectiveSelect } from "./Selectors";
import { AnalogTypeChip, ErrorNote, Loading, PageHeader, ScoreBar, StatusPill } from "./ui";

const EarthMap = dynamic(() => import("./EarthMap"), { ssr: false, loading: () => <div className="skeleton h-full w-full" /> });

type Match = ScoreResult & { name: string; lat: number; lon: number; analog_types: string[] };
type RefDetail = PlanetaryReference & { matches: Match[]; multipliers: Record<string, number>; cannot_replicate_on_earth: string[] };

export function PlanetExplorer({ body }: { body: Body }) {
  const { refs, meta } = useMeta();
  const labels = useCriteriaLabels();
  const u = useUrlState();
  const bodyRefs = refs.filter((r) => r.body === body);
  const selected = u.get("ref", meta?.default_reference[body] ?? bodyRefs[0]?.ref_id ?? "");
  const obj = u.get("obj", "general");
  const { data, error, loading } = useApi<RefDetail>(selected ? `/planetary-references/${selected}` : null, { objective: obj, top_k: 15 });
  const isMoon = body === "moon";

  return (
    <div>
      <PageHeader eyebrow={`Phase 3 · ${isMoon ? "Lunar" : "Martian"} reference viewer`} title={isMoon ? "Moon Reference Explorer" : "Mars Reference Explorer"}>
        {bodyRefs.length} {isMoon ? "lunar" : "Martian"} reference regions ({bodyRefs.slice(0, 4).map((r) => r.name.split(" (")[0]).join(", ")}{bodyRefs.length > 4 ? ", …" : ""}). Select a reference to see its matched Earth analog candidates.{" "}
        Coordinates are planetocentric latitude, east-positive longitude on the IAU {isMoon ? "Moon" : "Mars"} sphere — never WGS84, never drawn on the Earth map.
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <section className="space-y-4 xl:col-span-7" aria-label="Planetary map">
          <PlanetViewer body={body} refs={bodyRefs} selected={selected} onSelect={(id) => u.set({ ref: id })} />
          <section className="panel p-3" aria-labelledby="reflist-h">
            <h2 id="reflist-h" className="panel-title mb-2">Reference regions ({bodyRefs.length})</h2>
            <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {bodyRefs.map((r) => (
                <li key={r.ref_id}>
                  <button
                    onClick={() => u.set({ ref: r.ref_id })}
                    aria-pressed={r.ref_id === selected}
                    className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition ${r.ref_id === selected ? (isMoon ? "border-lunar-300/60 bg-lunar-200/10" : "border-mars-400/60 bg-mars-500/10") : "border-white/10 hover:bg-white/[0.04]"}`}
                  >
                    <span className="block font-medium text-white">{r.name}</span>
                    <span className="font-mono text-[11px] text-lunar-400">{fmtLat(r.lat)} {fmtLonEast(r.lon_east)} · {(r.status_class || r.region_type).replace(/_/g, " ")}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </section>

        <section className="space-y-4 xl:col-span-5" aria-label="Reference details and matches">
          <ErrorNote error={error} />
          {loading && !data && <div className="panel p-4"><Loading rows={8} /></div>}
          {data && (
            <>
              <article className="panel fade-in p-4" aria-labelledby="ref-title" data-testid="reference-detail">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="chip bg-white/5 text-lunar-100 ring-white/15" data-testid="status-class">{(data.status_class || data.region_type || "region").replace(/_/g, " ")}</span>
                  {data.not_an_approved_base_site && <span className="chip bg-amber-500/10 text-amber-200 ring-amber-400/30">not an approved base site</span>}
                </div>
                <h2 id="ref-title" className="mt-1 text-xl font-semibold text-white">{data.name}</h2>
                <p className="mt-2 text-sm text-lunar-200">{data.description}</p>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div><dt className="text-lunar-400">Latitude (planetocentric)</dt><dd className="font-mono text-lunar-100">{data.lat.toFixed(2)}°</dd></div>
                  <div><dt className="text-lunar-400">Longitude (+East)</dt><dd className="font-mono text-lunar-100">{data.lon_east.toFixed(2)}° / {data.lon_east_360?.toFixed(2)}° (0–360)</dd></div>
                  <div><dt className="text-lunar-400">Body radius (IAU mean)</dt><dd className="font-mono text-lunar-100">{data.body_radius_km} km</dd></div>
                  <div><dt className="text-lunar-400">Feature diameter</dt><dd className="font-mono text-lunar-100">{data.diameter_km ? `${data.diameter_km} km` : "—"}</dd></div>
                  <div className="col-span-2"><dt className="text-lunar-400">Source coordinate system</dt><dd className="text-lunar-100">{data.coordinate_system}</dd></div>
                  {data.lat <= -80 && (
                    <div className="col-span-2"><dt className="text-lunar-400">Great-circle distance to pole (sphere)</dt><dd className="font-mono text-lunar-100">{(((90 + data.lat) * Math.PI) / 180 * data.body_radius_km).toFixed(1)} km</dd></div>
                  )}
                </dl>
                <p className="mt-3 text-[11px] text-lunar-400">
                  Source:{" "}
                  {data.gazetteer_feature_id ? <a className="link" href={`https://planetarynames.wr.usgs.gov/Feature/${data.gazetteer_feature_id}`} target="_blank" rel="noreferrer">{data.citation}</a> : data.citation}
                </p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {data.traits.map((t) => <span key={t} className="chip bg-white/5 text-lunar-200 ring-white/10">{t}</span>)}
                </div>
                <div className="mt-3">
                  <p className="text-xs text-lunar-400">Earth analog environments sought:</p>
                  <div className="mt-1 flex flex-wrap gap-1">{data.analog_type_affinity.map((t) => <AnalogTypeChip key={t} type={t} />)}</div>
                </div>
                {Object.keys(data.multipliers).length > 0 && (
                  <p className="mt-3 text-xs text-lunar-300">
                    Reference weighting: {Object.entries(data.multipliers).map(([k, v]) => `${labels[k] ?? k} ×${v}`).join(" · ")}
                  </p>
                )}
              </article>

              <section className="panel p-4" aria-labelledby="matches-h">
                <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
                  <h2 id="matches-h" className="panel-title">Analog Match Explorer — Earth candidates</h2>
                  <div className="w-56"><ObjectiveSelect value={obj} onChange={(v) => u.set({ obj: v })} id={`obj-${body}`} body={body} /></div>
                </div>
                <ol className="space-y-1.5" data-testid="match-list">
                  {data.matches.map((m) => (
                    <li key={m.site_id} className="flex items-center gap-2">
                      <span className="w-6 text-right font-mono text-xs text-lunar-400">{m.rank ?? "–"}</span>
                      <Link className="w-40 truncate text-sm text-lunar-50 hover:text-mars-300 sm:w-56" href={`/explorer?site=${m.site_id}&ref=${selected}&obj=${obj}`} title={m.name}>{m.name}</Link>
                      <div className="flex-1"><ScoreBar score={m.score} low={m.score_low} high={m.score_high} /></div>
                      <span className="w-10 text-right font-mono text-xs">{m.score ?? "—"}</span>
                      <span className="hidden w-12 text-right text-[10px] text-lunar-400 sm:inline" title="evidence completeness">{pct(m.completeness)}</span>
                      <StatusPill status={m.status} />
                    </li>
                  ))}
                </ol>
                <div className="mt-3 flex gap-2">
                  <Link className="btn text-xs" href={`/explorer?ref=${selected}&obj=${obj}`}>Open in Earth Explorer</Link>
                  <Link className="btn text-xs" href={`/compare?ids=${data.matches.filter((m) => m.rank).slice(0, 3).map((m) => m.site_id).join(",")}&ref=${selected}&obj=${obj}`}>Compare top 3</Link>
                </div>
              </section>

              <div className="panel h-[300px] overflow-hidden">
                <EarthMap sites={data.matches} label="Globe of matched Earth analog sites" onSelect={(id) => window.location.assign(`/explorer?site=${id}&ref=${selected}&obj=${obj}`)} />
              </div>

              <section className="panel p-4">
                <h2 className="panel-title">What Earth cannot replicate here</h2>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-lunar-200">
                  {data.cannot_replicate_on_earth.map((c) => <li key={c}>{c}</li>)}
                </ul>
              </section>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
