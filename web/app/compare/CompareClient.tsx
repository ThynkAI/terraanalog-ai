"use client";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { buildQuery, useApi } from "@/lib/api";
import { fmtLat, fmtLonEarth, num, paramToWeights, pct, weightsToParam } from "@/lib/format";
import { useUrlState } from "@/lib/useUrlState";
import type { ClustersResponse, CompareResponse, RankingsResponse, SensitivityResponse, Site } from "@/lib/types";
import { BreakdownBar, ClusterScatter, DistributionChart, RadarCompare, RankingChart, SensitivityChart, SERIES } from "@/components/Charts";
import { useMeta } from "@/components/MetaContext";
import { ObjectiveSelect, ReferenceSelect } from "@/components/Selectors";
import { ErrorNote, Loading, PageHeader, ScoreBar, StatusPill, ValueTypeBadge } from "@/components/ui";

const ClusterArcMap = dynamic(() => import("@/components/ClusterArcMap"), { ssr: false, loading: () => <div className="aspect-[5/4] animate-pulse rounded-lg bg-white/5" /> });

const TABS = [
  { id: "compare", label: "Side-by-side comparison" },
  { id: "weights", label: "Custom Weight Lab" },
  { id: "sensitivity", label: "Sensitivity analysis" },
  { id: "discovery", label: "Discovery & distributions" },
];

export default function CompareClient() {
  const { meta } = useMeta();
  const u = useUrlState();
  const tab = u.get("tab", "compare");
  const ids = u.get("ids", "CA-HAU,AQ-MDV,US-LBN").split(",").filter(Boolean).slice(0, 4);
  const ref = u.get("ref", meta?.default_reference.moon ?? "moon-south-pole-region");
  const obj = u.get("obj", "general");
  const weights = paramToWeights(u.get("w"));
  const wParam = weightsToParam(weights);
  const all = useApi<{ sites: Site[] }>("/sites", { sort: "name", order: "asc" });

  const onTabKey = (e: React.KeyboardEvent, i: number) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const n = (i + (e.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length;
    u.set({ tab: TABS[n].id });
    document.getElementById(`tab-${TABS[n].id}`)?.focus();
  };

  return (
    <div>
      <PageHeader eyebrow="Phase 4 · Analog similarity dashboard" title="Site Comparison Laboratory">
        Compare up to four Earth sites against a planetary reference, tune the scoring weights, test the robustness of the ranking, and export a report.
      </PageHeader>

      <div className="panel no-print mb-4 grid grid-cols-1 gap-3 p-3 md:grid-cols-12">
        <div className="md:col-span-3"><ReferenceSelect value={ref} onChange={(v) => u.set({ ref: v })} /></div>
        <div className="md:col-span-3"><ObjectiveSelect value={obj} onChange={(v) => u.set({ obj: v })} /></div>
        <fieldset className="md:col-span-6">
          <legend className="label">Sites to compare (max 4)</legend>
          <div className="flex max-h-24 flex-wrap gap-1 overflow-y-auto">
            {(all.data?.sites ?? []).map((s) => {
              const on = ids.includes(s.site_id);
              return (
                <button key={s.site_id} aria-pressed={on} title={s.name}
                  className={`chip ${on ? "bg-signal-cyan/15 text-signal-cyan ring-signal-cyan/50" : "bg-white/[0.03] text-lunar-300 ring-white/10 hover:text-white"}`}
                  onClick={() => u.set({ ids: (on ? ids.filter((x) => x !== s.site_id) : [...ids, s.site_id].slice(-4)).join(",") || null })}>
                  {s.site_id}
                </button>
              );
            })}
          </div>
        </fieldset>
      </div>

      <div role="tablist" aria-label="Laboratory views" className="no-print mb-4 flex flex-wrap gap-1 border-b border-white/10">
        {TABS.map((t, i) => (
          <button key={t.id} id={`tab-${t.id}`} role="tab" aria-selected={tab === t.id} aria-controls={`panel-${t.id}`} tabIndex={tab === t.id ? 0 : -1}
            onKeyDown={(e) => onTabKey(e, i)} onClick={() => u.set({ tab: t.id })}
            className={`-mb-px rounded-t-lg border-b-2 px-3 py-2 text-sm ${tab === t.id ? "border-mars-400 text-white" : "border-transparent text-lunar-300 hover:text-white"}`}>
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "compare" && <CompareTab ids={ids} refId={ref} obj={obj} wParam={wParam} />}
        {tab === "weights" && <WeightLab refId={ref} obj={obj} weights={weights} setWeights={(w) => u.set({ w: weightsToParam(w) || null })} />}
        {tab === "sensitivity" && <SensitivityTab refId={ref} obj={obj} wParam={wParam} />}
        {tab === "discovery" && <DiscoveryTab refId={ref} obj={obj} />}
      </div>
    </div>
  );
}

function CompareTab({ ids, refId, obj, wParam }: { ids: string[]; refId: string; obj: string; wParam: string }) {
  const { meta } = useMeta();
  const { data, error, loading } = useApi<CompareResponse>(ids.length ? "/compare" : null, { ids: ids.join(","), ref_id: refId, objective: obj, weights: wParam || undefined });
  const radarData = useMemo(() => {
    if (!data) return [];
    return data.matrix.map((m) => {
      const row: Record<string, string | number | null> = { label: String(m.label).replace(" similarity", "").replace(" suitability", "") };
      data.sites.forEach((s) => (row[s.site_id] = (m[s.site_id] as number | null) ?? 0));
      return row;
    });
  }, [data]);
  if (!ids.length) return <p className="panel p-6 text-center text-lunar-300">Select at least one site above to compare.</p>;
  if (error) return <ErrorNote error={error} />;
  if (loading && !data) return <div className="panel p-4"><Loading rows={10} /></div>;
  if (!data) return null;
  const q = buildQuery({ ids: ids.join(","), ref_id: refId, objective: obj, weights: wParam || undefined });
  const exportUrl = `/api/export/compare.csv${q}`;
  const pdfUrl = `/api/export/compare.pdf${q}`;
  return (
    <div className="space-y-4" data-testid="compare-view">
      <div className="no-print flex flex-wrap items-center gap-2">
        <a className="btn" href={exportUrl} download>⬇ Export CSV report</a>
        <a className="btn btn-primary" href={pdfUrl} download data-testid="export-pdf">⬇ Download PDF report</a>
        <button className="btn" onClick={() => window.print()}>🖨 Print view</button>
        <button className="btn" onClick={() => navigator.clipboard?.writeText(window.location.href)}>Copy deep link</button>
        <span className="text-xs text-lunar-400">Report: {data.reference_name} · {meta?.objectives.find((o) => o.id === obj)?.label}{wParam ? ` · custom weights (${wParam})` : ""}</span>
      </div>
      {data.synthetic && <p className="rounded border border-pink-400/30 bg-pink-500/10 px-3 py-1.5 text-xs text-pink-200">SYNTHETIC FIXTURE DATA — scores are placeholders, not measurements.</p>}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <section className="panel p-4" aria-labelledby="radar-h">
          <h2 id="radar-h" className="panel-title mb-2">Radar comparison (criterion values 0–5)</h2>
          <RadarCompare data={radarData} series={data.sites.map((s) => ({ key: s.site_id, name: s.name.split(" (")[0] }))} />
          <p className="text-[11px] text-lunar-400">Missing values are drawn at 0 on the radar but are excluded from scores — see table.</p>
        </section>
        <section className="panel p-4" aria-labelledby="scores-h">
          <h2 id="scores-h" className="panel-title mb-3">Overall analog scores &amp; transparent breakdown</h2>
          <ul className="space-y-4">
            {data.sites.map((s, i) => (
              <li key={s.site_id}>
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: SERIES[i] }} aria-hidden="true" />
                  <span className="flex-1 text-sm font-medium text-white">{s.name}</span>
                  <StatusPill status={s.result.status} />
                  <span className="font-mono text-lg text-white">{s.result.score ?? "—"}</span>
                </div>
                <p className="ml-4 text-[11px] text-lunar-400">rank {s.result.rank ?? "unranked"} · range {s.result.score_low}–{s.result.score_high} · completeness {pct(s.result.completeness)} · confidence {pct(s.result.confidence)}</p>
                <div className="ml-4 mt-1"><ScoreBar score={s.result.score} low={s.result.score_low} high={s.result.score_high} /></div>
                <div className="ml-4 mt-2"><BreakdownBar breakdown={s.result.breakdown} /></div>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="panel overflow-x-auto p-4" aria-labelledby="table-h">
        <h2 id="table-h" className="panel-title mb-2">Side-by-side criteria (value · value type)</h2>
        <table className="table-base min-w-[720px]">
          <caption className="sr-only">Criterion values for each compared site with data value types</caption>
          <thead>
            <tr>
              <th scope="col">Criterion</th>
              {data.sites.map((s) => <th scope="col" key={s.site_id}>{s.name.split(" (")[0]}</th>)}
              <th scope="col">Spread</th>
            </tr>
          </thead>
          <tbody>
            {data.matrix.map((m) => (
              <tr key={String(m.criterion_id)}>
                <th scope="row" className="text-left font-normal text-lunar-200">{m.label}</th>
                {data.sites.map((s) => (
                  <td key={s.site_id}>
                    <span className="mr-1.5 font-mono">{m[s.site_id] ?? "—"}</span>
                    <ValueTypeBadge type={String(m[`${s.site_id}__type`])} compact />
                  </td>
                ))}
                <td className="font-mono text-lunar-300">{m.spread ?? "—"}</td>
              </tr>
            ))}
            <tr>
              <th scope="row" className="text-left font-normal text-lunar-200">Coordinates</th>
              {data.sites.map((s) => <td key={s.site_id} className="font-mono text-xs">{fmtLat(s.lat)} {fmtLonEarth(s.lon)}</td>)}
              <td />
            </tr>
            <tr>
              <th scope="row" className="text-left font-normal text-lunar-200">Climate / geology</th>
              {data.sites.map((s) => <td key={s.site_id} className="text-xs text-lunar-300">{s.climate} — {s.geology}</td>)}
              <td />
            </tr>
            <tr>
              <th scope="row" className="text-left font-normal text-lunar-200">Mission use cases</th>
              {data.sites.map((s) => <td key={s.site_id} className="text-xs text-lunar-300">{s.mission_objectives.filter((o) => o !== "general").join(", ").replace(/_/g, " ")}</td>)}
              <td />
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  );
}

function WeightLab({ refId, obj, weights, setWeights }: { refId: string; obj: string; weights: Record<string, number>; setWeights: (w: Record<string, number>) => void }) {
  const { meta } = useMeta();
  const [local, setLocal] = useState<Record<string, number>>(weights);
  const wParam = weightsToParam(local);
  const base = useApi<RankingsResponse>("/rankings", { ref_id: refId, objective: obj });
  const live = useApi<RankingsResponse>("/rankings", { ref_id: refId, objective: obj, weights: wParam || undefined }, 120);
  const baseRank: Record<string, number | null> = {};
  base.data?.rankings.forEach((r) => (baseRank[r.site_id] = r.rank));
  const update = (k: string, v: number) => {
    const n = { ...local, [k]: v };
    setLocal(n);
    setWeights(n);
  };
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <section className="panel p-4 lg:col-span-4" aria-labelledby="wl-h">
        <h2 id="wl-h" className="panel-title">Custom Weight Laboratory</h2>
        <p className="mt-1 text-xs text-lunar-400">Multiply each criterion&apos;s documented weight (0× disables it). Rankings recalculate immediately via the scoring API.</p>
        <div className="mt-3 space-y-3">
          {(meta?.criteria ?? []).map((c) => {
            const v = local[c.id] ?? 1;
            const eff = live.data?.effective_weights[c.id];
            return (
              <div key={c.id}>
                <label htmlFor={`w-${c.id}`} className="flex justify-between text-xs text-lunar-200">
                  <span>{c.label}</span>
                  <span className="font-mono text-white">×{v.toFixed(2)} <span className="text-lunar-400">(w={num(eff, 2)})</span></span>
                </label>
                <input id={`w-${c.id}`} type="range" min={0} max={3} step={0.05} value={v} onChange={(e) => update(c.id, Number(e.target.value))} className="w-full accent-mars-500" aria-valuetext={`multiplier ${v.toFixed(2)}`} />
              </div>
            );
          })}
        </div>
        <button className="btn mt-3 w-full" onClick={() => { setLocal({}); setWeights({}); }}>Reset to documented weights</button>
      </section>
      <section className="panel p-4 lg:col-span-8" aria-labelledby="wl-r" aria-busy={live.loading}>
        <h2 id="wl-r" className="panel-title mb-2">Live re-ranking {live.loading && <span className="text-lunar-400">· updating…</span>}</h2>
        <ErrorNote error={live.error} />
        {live.data && (
          <>
            <RankingChart rows={live.data.rankings.filter((r) => r.score !== null).map((r) => ({ name: r.name.split(" (")[0], score: r.score, low: r.score_low, high: r.score_high }))} />
            <table className="table-base mt-3 text-xs" data-testid="weightlab-table">
              <thead><tr><th>Rank</th><th>Site</th><th>Score</th><th>Δ rank vs documented</th><th>Completeness</th></tr></thead>
              <tbody>
                {live.data.rankings.map((r) => {
                  const d = r.rank && baseRank[r.site_id] ? baseRank[r.site_id]! - r.rank : null;
                  return (
                    <tr key={r.site_id}>
                      <td className="font-mono">{r.rank ?? "–"}</td>
                      <td>{r.name}</td>
                      <td className="font-mono">{r.score ?? "—"}</td>
                      <td className={`font-mono ${d && d > 0 ? "text-emerald-300" : d && d < 0 ? "text-red-300" : "text-lunar-400"}`}>{d === null ? "—" : d > 0 ? `▲${d}` : d < 0 ? `▼${-d}` : "="}</td>
                      <td>{pct(r.completeness)} <StatusPill status={r.status} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}
      </section>
    </div>
  );
}

function SensitivityTab({ refId, obj, wParam }: { refId: string; obj: string; wParam: string }) {
  const { meta } = useMeta();
  const [crit, setCrit] = useState("geology");
  const all = useApi<SensitivityResponse>("/sensitivity", { ref_id: refId, objective: obj, weights: wParam || undefined, top_n: 6 });
  const names = useApi<{ sites: Site[] }>("/sites");
  const nm: Record<string, string> = {};
  names.data?.sites.forEach((s) => (nm[s.site_id] = s.name.split(" (")[0]));
  const sweep = all.data?.sweeps[crit] ?? [];
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <section className="panel p-4 lg:col-span-8" aria-labelledby="sens-h">
        <div className="mb-2 flex flex-wrap items-end justify-between gap-2">
          <h2 id="sens-h" className="panel-title">Score response to one criterion&apos;s weight (0× → 2×)</h2>
          <div className="w-60">
            <label htmlFor="sens-crit" className="label">Criterion</label>
            <select id="sens-crit" className="select" value={crit} onChange={(e) => setCrit(e.target.value)}>
              {(meta?.criteria ?? []).map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </div>
        </div>
        <ErrorNote error={all.error} />
        {all.loading && !all.data ? <Loading rows={6} /> : <SensitivityChart data={sweep as Record<string, number | null>[]} sites={all.data?.tracked_sites ?? []} names={nm} />}
      </section>
      <section className="panel p-4 lg:col-span-4" aria-labelledby="stab-h">
        <h2 id="stab-h" className="panel-title mb-2">Rank stability (±50 % weight)</h2>
        <p className="mb-2 text-xs text-lunar-400">Max rank shift among the top {all.data?.tracked_sites.length ?? 0} sites when each criterion weight is halved or increased by half. Lower = more robust.</p>
        <ul className="space-y-1.5 text-sm">
          {(meta?.criteria ?? []).map((c) => {
            const s = all.data?.max_rank_shift_by_criterion[c.id] ?? 0;
            return (
              <li key={c.id} className="flex items-center gap-2">
                <span className="flex-1 text-lunar-200">{c.label}</span>
                <div className="h-2 w-24 overflow-hidden rounded bg-white/5"><div className="h-full bg-mars-500" style={{ width: `${Math.min(100, s * 25)}%` }} /></div>
                <span className="w-8 text-right font-mono text-xs">{s}</span>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}

function DiscoveryTab({ refId, obj }: { refId: string; obj: string }) {
  const { meta } = useMeta();
  const scored = useApi<{ sites: Site[] }>("/sites", { ref_id: refId, objective: obj });
  const [k, setK] = useState(4);
  const [x, setX] = useState("thermal");
  const [y, setY] = useState("terrain");
  const cl = useApi<ClustersResponse>("/clusters", { k });
  const feats = useApi<{ sites: { site_id: string; name: string; values: Record<string, { value: number | null; value_type: string }> }[] }>("/features");
  const values: Record<string, Record<string, { v: number | null; t: string }>> = {};
  const nm: Record<string, string> = {};
  (feats.data?.sites ?? []).forEach((s) => {
    nm[s.site_id] = s.name;
    values[s.site_id] = {};
    Object.entries(s.values).forEach(([c, e]) => (values[s.site_id][c] = { v: e.value, t: e.value_type }));
  });
  const points = Object.entries(values)
    .filter(([, v]) => v[x]?.v !== null && v[x]?.v !== undefined && v[y]?.v !== null && v[y]?.v !== undefined)
    .map(([sid, v]) => ({ x: v[x].v as number, y: v[y].v as number, cluster: cl.data?.assignments[sid] ?? 0, name: nm[sid] ?? sid }));
  const excluded = Object.keys(values).length - points.length;
  const geo = useMemo(() => (cl.data && scored.data ? scored.data.sites.filter((s) => s.site_id in cl.data!.assignments).map((s) => ({ site_id: s.site_id, name: s.name, lat: s.lat, lon: s.lon, score: s.score ?? null, cluster: cl.data!.assignments[s.site_id] })) : []), [cl.data, scored.data]);
  const dist = (meta?.criteria ?? []).map((c) => c.id);
  const [dc, setDc] = useState("ice_permafrost");
  const hist = [0, 1, 2, 3, 4, 5].map((b) => {
    const row: Record<string, number | string> = { bin: String(b), provisional: 0, synthetic: 0, measured: 0, modeled: 0 };
    Object.values(values).forEach((v) => {
      const e = v[dc];
      if (e && e.v !== null && Math.round(e.v) === b) row[e.t] = (Number(row[e.t]) || 0) + 1;
    });
    return row;
  });
  const missingCount = Object.values(values).filter((v) => !v[dc] || v[dc].v === null).length;
  const crits = meta?.criteria ?? [];
  const lbl = (id: string) => crits.find((c) => c.id === id)?.label ?? id;
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <section className="panel p-4 lg:col-span-7" aria-labelledby="disc-h">
        <h2 id="disc-h" className="panel-title">Analog Discovery View — clusters of candidate environments</h2>
        <div className="mt-2 grid grid-cols-3 gap-2">
          <div><label className="label" htmlFor="cx">X axis</label><select id="cx" className="select" value={x} onChange={(e) => setX(e.target.value)}>{crits.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}</select></div>
          <div><label className="label" htmlFor="cy">Y axis</label><select id="cy" className="select" value={y} onChange={(e) => setY(e.target.value)}>{crits.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}</select></div>
          <div><label className="label" htmlFor="ck">Clusters (k)</label><select id="ck" className="select" value={k} onChange={(e) => setK(Number(e.target.value))}>{[2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n}</option>)}</select></div>
        </div>
        <ClusterScatter points={points} xLabel={lbl(x)} yLabel={lbl(y)} />
        {excluded > 0 && <p className="text-[11px] text-lunar-400">{excluded} site(s) omitted from this plot because one of the axis values is missing (not imputed).</p>}
        <p className="text-[11px] text-lunar-400">Method: {cl.data?.method}. Overlapping points share identical values.</p>
      </section>
      <section className="panel p-4 lg:col-span-5" aria-labelledby="cl-h">
        <h2 id="cl-h" className="panel-title mb-2">Cluster membership</h2>
        <ul className="space-y-2">
          {(cl.data?.clusters ?? []).map((c, i) => (
            <li key={c.cluster} className="rounded-lg border border-white/10 p-2 text-xs">
              <p className="font-medium text-white"><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full" style={{ background: SERIES[i % SERIES.length] }} />Cluster {c.cluster + 1}: {c.label}</p>
              <p className="mt-0.5 text-lunar-400">Defining criteria: {c.defining_criteria.map(lbl).join(", ")}</p>
              <p className="mt-0.5 text-lunar-200">{c.members.map((m) => nm[m]?.split(" (")[0] ?? m).join(" · ")}</p>
            </li>
          ))}
        </ul>
      </section>
      <section className="panel p-4 lg:col-span-7" aria-labelledby="geo-h">
        <h2 id="geo-h" className="panel-title mb-2">Where the clusters are — similar environments across the globe</h2>
        <ClusterArcMap sites={geo} />
      </section>
      <section className="panel p-4 lg:col-span-5" aria-labelledby="dist-h">
        <div className="mb-2 flex flex-wrap items-end justify-between gap-2">
          <h2 id="dist-h" className="panel-title">Feature distribution across all sites (stacked by value type)</h2>
          <div className="w-60"><label className="label" htmlFor="dc">Criterion</label><select id="dc" className="select" value={dc} onChange={(e) => setDc(e.target.value)}>{dist.map((c) => <option key={c} value={c}>{lbl(c)}</option>)}</select></div>
        </div>
        <DistributionChart data={hist} />
        <p className="text-[11px] text-lunar-400">{missingCount} site(s) have no value for this criterion (shown as missing, not zero).</p>
      </section>
    </div>
  );
}
