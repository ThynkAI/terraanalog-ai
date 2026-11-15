"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useApi } from "@/lib/api";
import { ANALOG_TYPE_COLORS } from "@/lib/constants";
import { downloadText, parseLatLon, toCSV } from "@/lib/format";
import { useUrlState } from "@/lib/useUrlState";
import type { Basemap } from "@/components/EarthMap";
import { RankingChart } from "@/components/Charts";
import { MapLegend } from "@/components/MapLegend";
import { useMeta } from "@/components/MetaContext";
import { RecommendPanel } from "@/components/RecommendPanel";
import { ObjectiveSelect, RefNotes, ReferenceSelect } from "@/components/Selectors";
import { SiteDetail } from "@/components/SiteDetail";
import { AnalogIcon, ErrorNote, Loading, PageHeader, ScoreBar, StatusPill } from "@/components/ui";
import type { Site } from "@/lib/types";

const EarthMap = dynamic(() => import("@/components/EarthMap"), { ssr: false, loading: () => <div className="skeleton h-full w-full" /> });

export default function ExplorerClient() {
  const { meta, refs } = useMeta();
  const u = useUrlState();
  const refParam = u.get("ref");
  const ref = refParam || meta?.default_reference.moon || "";
  const obj = u.get("obj", "general");
  const body = u.get("body");
  const type = u.get("type");
  const climate = u.get("climate");
  const geology = u.get("geology");
  const mobj = u.get("mobj");
  const minScore = Number(u.get("minScore", "0"));
  const minConf = Number(u.get("minConf", "0"));
  const hideInsufficient = u.get("hideIns") === "1";
  const selected = u.get("site") || null;
  const compare = u.get("compare").split(",").filter(Boolean);
  const [search, setSearch] = useState(u.get("q"));
  const [radius, setRadius] = useState(Number(u.get("r", "2000")));
  const [basemap, setBasemap] = useState<Basemap>((u.get("basemap") as Basemap) || "vector");
  const [projection, setProjection] = useState<"globe" | "mercator">(u.get("proj") === "mercator" ? "mercator" : "globe");
  const [focus, setFocus] = useState<{ lat: number; lon: number; zoom?: number } | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const q = u.get("q");
  const coords = parseLatLon(q);
  const { data, error, loading } = useApi<{ count: number; sites: Site[]; notes?: string[] }>(meta && ref ? "/sites" : null, {
    ref_id: ref, objective: obj, body, analog_type: type, climate, geology, mission_objective: mobj,
    min_score: minScore || undefined, min_confidence: minConf || undefined, include_insufficient: !hideInsufficient,
    q: coords ? undefined : q, near: coords ? `${coords.lat},${coords.lon}` : undefined, radius_km: coords ? radius : undefined,
    sort: coords ? "distance" : "score", order: coords ? "asc" : "desc",
  });
  const sites = useMemo(() => data?.sites ?? [], [data]);
  const refObj = refs.find((r) => r.ref_id === ref);
  const objBody = (o: string) => meta?.objective_bodies?.[o] ?? null;
  const notes = [
    ...(!refParam && refObj ? [`No planetary reference selected — using the ${refObj.body === "moon" ? "Moon" : "Mars"} default reference ${refObj.name}.`] : []),
    ...(data?.notes ?? []).filter((n) => !n.startsWith("No planetary reference selected")),
  ];
  const manyClimates = (meta?.climates.length ?? 0) > 12;

  useEffect(() => {
    if (coords) setFocus({ lat: coords.lat, lon: coords.lon, zoom: 3 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);
  useEffect(() => {
    if (!selected) return;
    const s = sites.find((x) => x.site_id === selected);
    if (s) setFocus({ lat: s.lat, lon: s.lon, zoom: 1.7 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, data]);

  const setBody = (b: string) => {
    const patch: Record<string, string | null> = { body: b || null };
    if (b && refObj && refObj.body !== b) {
      patch.ref = meta?.default_reference[b as "moon" | "mars"] ?? null;
      const ob = objBody(obj);
      if (ob && ob !== b) patch.obj = null;
    }
    u.set(patch);
  };
  const setRef = (r: string) => {
    const rb = refs.find((x) => x.ref_id === r)?.body;
    const ob = objBody(obj);
    u.set({ ref: r, body: body && rb && body !== rb ? rb : body || null, ...(ob && rb && ob !== rb ? { obj: null } : {}) });
  };
  const toggleCompare = (id: string) => {
    const next = compare.includes(id) ? compare.filter((x) => x !== id) : [...compare, id].slice(-4);
    u.set({ compare: next.join(",") || null });
  };
  const exportCsv = () => {
    downloadText(
      `terraanalog_rankings_${ref}_${obj}.csv`,
      toCSV(sites.map((s) => ({ rank: s.rank ?? "", site_id: s.site_id, name: s.name, lat: s.lat, lon: s.lon, score: s.score ?? "", score_low: s.score_low, score_high: s.score_high, completeness: s.completeness, confidence: s.confidence, status: s.status, provenance: s.provenance })),
        meta?.data_status.synthetic ? "SYNTHETIC FIXTURE DATA — NOT REAL MEASUREMENTS" : undefined),
    );
  };

  const filters = (
    <div className="space-y-3">
      <fieldset>
        <legend className="label">Target body</legend>
        <div className="grid grid-cols-3 gap-1" role="radiogroup">
          {[["", "All"], ["moon", "☾ Moon"], ["mars", "♂ Mars"]].map(([v, l]) => (
            <button key={v} role="radio" aria-checked={body === v} className={`btn px-2 py-1 text-xs ${body === v ? "border-mars-400 bg-mars-600/30" : ""}`} onClick={() => setBody(v)}>{l}</button>
          ))}
        </div>
      </fieldset>
      <div>
        <label htmlFor="f-type" className="label">Analog type</label>
        <select id="f-type" className="select" value={type} onChange={(e) => u.set({ type: e.target.value })}>
          <option value="">All types</option>
          {Object.entries(meta?.analog_types ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="f-climate" className="label">{manyClimates ? "Climate contains" : "Climate"}</label>
        {manyClimates ? (
          <input id="f-climate" className="input" value={climate} placeholder="e.g. permafrost, ERA5, arid" onChange={(e) => u.set({ climate: e.target.value || null })} />
        ) : (
          <select id="f-climate" className="select" value={climate} onChange={(e) => u.set({ climate: e.target.value })}>
            <option value="">All climates</option>
            {(meta?.climates ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
      </div>
      <div>
        <label htmlFor="f-geo" className="label">Geology contains</label>
        <input id="f-geo" className="input" value={geology} placeholder="e.g. basalt, impact, permafrost" onChange={(e) => u.set({ geology: e.target.value })} />
      </div>
      <div>
        <label htmlFor="f-mobj" className="label">Supports mission use</label>
        <select id="f-mobj" className="select" value={mobj} onChange={(e) => u.set({ mobj: e.target.value })}>
          <option value="">Any</option>
          {(meta?.objectives ?? []).filter((o) => o.id !== "general").map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="f-min" className="label">Minimum score: <span className="font-mono text-white">{minScore}</span></label>
        <input id="f-min" type="range" min={0} max={90} step={5} value={minScore} onChange={(e) => u.set({ minScore: e.target.value === "0" ? null : e.target.value })} className="w-full accent-mars-500" />
      </div>
      <div>
        <label htmlFor="f-conf" className="label">Minimum confidence: <span className="font-mono text-white">{Math.round(minConf * 100)}%</span></label>
        <input id="f-conf" type="range" min={0} max={0.9} step={0.05} value={minConf} onChange={(e) => u.set({ minConf: e.target.value === "0" ? null : e.target.value })} className="w-full accent-mars-500" />
      </div>
      <label className="flex items-center gap-2 text-xs text-lunar-200">
        <input type="checkbox" checked={hideInsufficient} onChange={(e) => u.set({ hideIns: e.target.checked ? "1" : null })} className="accent-mars-500" />
        Hide sites with insufficient evidence
      </label>
      <button className="btn w-full text-xs" onClick={() => { setSearch(""); u.set({ body: null, type: null, climate: null, geology: null, mobj: null, minScore: null, minConf: null, hideIns: null, q: null }); }}>Reset filters</button>
    </div>
  );

  return (
    <div>
      <PageHeader eyebrow="Phase 2 · Interactive global map" title="Earth Analog Explorer">
        Choose a Moon or Mars reference and a mission objective; sites are ranked live with transparent scoring. Click a marker or list item for evidence.
      </PageHeader>

      <div className="panel mb-4 grid grid-cols-1 gap-3 p-3 sm:grid-cols-2 lg:grid-cols-12">
        <div className="lg:col-span-3"><ReferenceSelect value={ref} onChange={setRef} /></div>
        <div className="lg:col-span-2"><ObjectiveSelect value={obj} onChange={(v) => u.set({ obj: v })} body={refObj?.body} /></div>
        <form className="lg:col-span-4" role="search" onSubmit={(e) => { e.preventDefault(); u.set({ q: search.trim() || null, r: String(radius) }); }}>
          <label htmlFor="geo-search" className="label">Geographic search — name, country, or “lat, lon”</label>
          <div className="flex gap-1.5">
            <input id="geo-search" className="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Iceland · Arizona · 75.4, -89.7" />
            {parseLatLon(search) && (
              <select aria-label="Search radius" className="select w-28" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
                {[250, 500, 1000, 2000, 5000].map((r) => <option key={r} value={r}>{r} km</option>)}
              </select>
            )}
            <button className="btn" type="submit">Search</button>
          </div>
        </form>
        <div className="lg:col-span-2">
          <label htmlFor="basemap" className="label">Basemap</label>
          <select id="basemap" className="select" value={basemap} onChange={(e) => { setBasemap(e.target.value as Basemap); u.set({ basemap: e.target.value === "vector" ? null : e.target.value }); }}>
            <option value="vector">Vector (offline)</option>
            <option value="satellite">Satellite — NASA Blue Marble</option>
            <option value="terrain">Terrain — ASTER shaded relief</option>
          </select>
        </div>
        <div className="lg:col-span-1">
          <span className="label">View</span>
          <button className="btn w-full" aria-pressed={projection === "globe"} onClick={() => { const p = projection === "globe" ? "mercator" : "globe"; setProjection(p); u.set({ proj: p === "globe" ? null : p }); }}>
            {projection === "globe" ? "🌐 Globe" : "▭ 2D"}
          </button>
        </div>
      </div>

      <RefNotes notes={notes} className="mb-3" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <aside className="space-y-4 lg:col-span-3" aria-label="Filters and ranked sites">
          <section className="panel p-3">
            <div className="flex items-center justify-between">
              <h2 className="panel-title">Filters</h2>
              <button className="btn btn-ghost px-2 py-0.5 text-xs lg:hidden" aria-expanded={filtersOpen} aria-controls="filters-body" onClick={() => setFiltersOpen((o) => !o)}>{filtersOpen ? "Hide" : "Show"}</button>
            </div>
            <div id="filters-body" className={`mt-3 ${filtersOpen ? "" : "hidden lg:block"}`}>{filters}</div>
          </section>
          <section className="panel p-3" aria-labelledby="ranked-h">
            <div className="flex items-center justify-between">
              <h2 id="ranked-h" className="panel-title">Ranked sites {data && <span className="text-lunar-400">({data.count})</span>}</h2>
              <button className="btn btn-ghost px-2 py-0.5 text-xs" onClick={exportCsv} disabled={!sites.length}>CSV</button>
            </div>
            <ErrorNote error={error} />
            {loading && !data ? <div className="mt-3"><Loading rows={6} /></div> : (
              <ol className="mt-2 max-h-[560px] space-y-1 overflow-y-auto pr-1" data-testid="ranked-list">
                {sites.length === 0 && <li className="py-6 text-center text-sm text-lunar-400">No sites match these filters.</li>}
                {sites.map((s) => (
                  <li key={s.site_id} className={`rounded-lg border px-2 py-1.5 transition ${selected === s.site_id ? "border-mars-400/60 bg-mars-500/10" : "border-transparent hover:bg-white/[0.04]"}`}>
                    <div className="flex items-center gap-2">
                      <span className="w-6 text-right font-mono text-xs text-lunar-400">{s.rank ?? "–"}</span>
                      <AnalogIcon type={s.analog_types[0]} size={14} color={ANALOG_TYPE_COLORS[s.analog_types[0]]} />
                      <button className="min-w-0 flex-1 truncate text-left text-sm text-lunar-50 hover:text-white" onClick={() => u.set({ site: s.site_id })} aria-current={selected === s.site_id ? "true" : undefined}>
                        {s.name}
                      </button>
                      <span className="font-mono text-xs text-lunar-200">{s.score ?? "—"}</span>
                      <input type="checkbox" aria-label={`Compare ${s.name}`} checked={compare.includes(s.site_id)} onChange={() => toggleCompare(s.site_id)} className="accent-signal-cyan" />
                    </div>
                    <div className="ml-8 mt-1 flex items-center gap-2">
                      <div className="flex-1"><ScoreBar score={s.score} low={s.score_low} high={s.score_high} /></div>
                      <StatusPill status={s.status} />
                      {s.distance_km !== undefined && <span className="text-[10px] text-lunar-400">{Math.round(s.distance_km)} km</span>}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </aside>

        <section className="space-y-4 lg:col-span-6" aria-label="Map">
          <div className="panel relative h-[420px] overflow-hidden sm:h-[560px]">
            <EarthMap
              sites={sites}
              selectedId={selected}
              compareIds={compare}
              onSelect={(id) => u.set({ site: id })}
              basemap={basemap}
              projection={projection}
              focus={focus}
            />
          </div>
          <MapLegend />
          <section className="panel p-3" aria-labelledby="rc-h">
            <h2 id="rc-h" className="panel-title mb-2">Ranking chart · {refObj?.name ?? ref} · whiskers = plausible range from missing data</h2>
            <RankingChart rows={sites.filter((s) => s.score !== null && s.score !== undefined).slice(0, 12).map((s) => ({ name: s.name.split(" (")[0], score: s.score ?? null, low: s.score_low ?? 0, high: s.score_high ?? 0 }))} />
          </section>
        </section>

        <aside className="lg:col-span-3" aria-label="Details">
          <div className="panel lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
            {selected ? (
              <SiteDetail siteId={selected} refId={ref} objective={obj} onClose={() => u.set({ site: null })} onCompare={toggleCompare} inCompare={compare.includes(selected)} />
            ) : (
              <div className="p-1">
                <RecommendPanel compact onPick={(sid, r, o) => u.set({ site: sid, ref: r, obj: o, body: null })} />
              </div>
            )}
          </div>
        </aside>
      </div>

      {compare.length > 0 && (
        <div className="no-print fixed inset-x-0 bottom-0 z-30 border-t border-white/10 bg-space-950/95 px-4 py-2 backdrop-blur" role="region" aria-label="Comparison tray">
          <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-2">
            <span className="text-xs text-lunar-300">Comparing ({compare.length}/4):</span>
            {compare.map((id) => (
              <button key={id} className="chip bg-signal-cyan/10 text-signal-cyan ring-signal-cyan/40" onClick={() => toggleCompare(id)} aria-label={`Remove ${id} from comparison`}>{id} ✕</button>
            ))}
            <Link href={`/compare?ids=${compare.join(",")}&ref=${ref}&obj=${obj}`} className="btn btn-primary ml-auto text-xs">Open Comparison Lab →</Link>
          </div>
        </div>
      )}
    </div>
  );
}
