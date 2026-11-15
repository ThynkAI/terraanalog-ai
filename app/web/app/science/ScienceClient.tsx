"use client";
import Link from "next/link";
import { useState } from "react";
import { useApi } from "@/lib/api";
import { useUrlState } from "@/lib/useUrlState";
import { downloadText, toCSV } from "@/lib/format";
import type { CaseStudiesResponse, CaseStudy } from "@/lib/science";
import { StrictEvidencePanel } from "@/components/StrictEvidencePanel";
import { PlanetViewer } from "@/components/PlanetViewer";
import { ErrorNote, Loading, PageHeader, ScoreBar } from "@/components/ui";

const n = (value: number | null | undefined, digits = 2) => value == null ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: digits });
function CaseImage({ study }: { study: CaseStudy }) {
  const [failed, setFailed] = useState(false);
  const image = study.site.imagery;
  return <figure className="min-w-0 rounded-xl border border-white/10 bg-space-950 p-3">
    <p className="panel-title mb-2">Earth / {study.site.country}</p>
    {image && !failed ? <img src={image.url} alt={`${study.site.name} geographic context; not a scale-matched field survey`} onError={() => setFailed(true)} loading="lazy" className="h-56 w-full rounded-lg object-cover" /> : <div className="flex h-56 items-center justify-center rounded-lg bg-space-800 text-sm text-lunar-300">Site photograph unavailable; measurements remain available below.</div>}
    <figcaption className="mt-2 text-[11px] leading-relaxed text-lunar-300">{study.site.name}. Archival geographic context; conditions may differ today. {image && <><a className="link" href={image.attribution_page || image.url} target="_blank" rel="noreferrer">{image.credit}</a>{" · "}<a className="link" href={image.license_url ?? undefined} target="_blank" rel="noreferrer">{image.license}</a></>}</figcaption>
  </figure>;
}

export default function ScienceClient() {
  const { data, loading, error, retry } = useApi<CaseStudiesResponse>("/case-studies");
  const url = useUrlState();
  const requested = url.get("case");
  const study = data?.cases.find((c) => c.id === requested) ?? data?.cases[0];
  const stress = url.get("stress") === "1";
  const [copied, setCopied] = useState(false);
  const baseline = study?.comparisons.find((row) => row.site_id === study.site_id)?.result;
  const exportCase = (c: CaseStudy) => downloadText(`terraanalog_${c.id}_evidence.json`, JSON.stringify({ reviewed_on: data?.reviewed_on, review_scope: data?.review_scope, scoring_note: data?.scoring_note, case_study: c }, null, 2), "application/json");
  return <div className="space-y-5">
    <PageHeader eyebrow="From a ranking to a research decision" title="Scientific Case Studies">Three source-reviewed investigations connect regional measurements to practical field questions. Compare the benchmarks, challenge the assumptions, and see what still needs to be measured.</PageHeader>
    <ErrorNote error={error} />
    {error && <button className="btn" onClick={retry}>Retry scientific cases</button>}
    {loading && !data && <Loading rows={6} />}
    {data && !data.available && <p className="panel p-5">{data.reason}</p>}
    {data?.available && study && <>
      <nav aria-label="Scientific case selection" className="grid gap-3 md:grid-cols-3">
        {data.cases.map((c, i) => <button key={c.id} onClick={() => { url.set({ case: c.id, stress: null }); setCopied(false); }} aria-pressed={study.id === c.id} className={`min-w-0 rounded-xl border p-4 text-left transition ${study.id === c.id ? "border-mars-400 bg-mars-500/10" : "border-white/10 bg-space-800 hover:border-white/30"}`}><span className="font-mono text-xs text-mars-300">0{i + 1} / {c.reference.body.toUpperCase()}</span><span className="mt-2 block text-sm font-semibold text-white">{c.title}</span><span className="mt-2 block text-xs text-lunar-300">{c.novelty_status}</span></button>)}
      </nav>
      <nav className="no-print flex flex-wrap gap-2" aria-label="Case study sections">
        {[["case-overview", "Overview"], ["measurement-title", "Measurements"], ["benchmark-title", "Benchmarks"], ["case-evidence", "Evidence"], ["case-field-plan", "Field plan"]].map(([id, label]) => <a key={id} href={`#${id}`} className="btn btn-ghost text-xs">{label} <span aria-hidden="true">↓</span></a>)}
      </nav>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Baseline case summary">
        {[["Baseline proxy score", `${n(baseline?.score, 1)} / 100`], ["Evidence completeness", baseline ? `${n(baseline.completeness * 100, 1)}%` : "—"], ["Full-catalog rank", baseline?.rank ? `#${baseline.rank}` : "—"], ["Compared with best benchmark", study.advantage_vs_best_benchmark == null ? "—" : `${study.advantage_vs_best_benchmark > 0 ? "+" : ""}${n(study.advantage_vs_best_benchmark, 1)} points`]].map(([label, value]) => <div key={label} className="rounded-xl border border-white/10 bg-space-900/70 p-4"><p className="text-[11px] text-lunar-300">{label}</p><p className="mt-2 font-mono text-xl text-white">{value}</p></div>)}
      </div>
      <article className="space-y-5" data-testid="scientific-case">
        <section id="case-overview" className="panel p-5 sm:p-7">
          <p className="panel-title text-signal-cyan">{study.objective_label} / {study.site_id}</p>
          <h2 className="mt-3 text-2xl font-semibold text-white">{study.question}</h2>
          <p className="mt-3 text-sm leading-relaxed text-lunar-200">{study.interpretation}</p>
          <div className="mt-4 rounded-lg border border-amber-300/20 bg-amber-400/5 p-3 text-sm text-lunar-100"><strong className="text-amber-200">Novelty assessment: {study.novelty_status}.</strong> {study.novelty_finding}</div>
          <p className="mt-3 text-xs text-lunar-300">Review date: {data.reviewed_on}. {data.review_scope}</p>
        </section>
        <section className="panel p-5" aria-label="Visual geographic context">
          <h3 className="panel-title mb-3">Two worlds / geographic context</h3>
          <div className="grid gap-4 lg:grid-cols-2">
            <CaseImage key={study.id} study={study} />
            <div className="min-w-0 rounded-xl border border-white/10 bg-space-950 p-3"><p className="panel-title mb-2">{study.reference.body} / {study.ref_id}</p><PlanetViewer key={study.ref_id} body={study.reference.body} refs={[study.reference]} selected={study.ref_id} onSelect={() => {}} /><p className="mt-2 text-xs text-lunar-300">{study.reference.name}. {study.reference.coordinate_system}. This reference is not an approved permanent base.</p></div>
          </div>
          <p className="mt-3 text-xs text-lunar-300">The photograph and orbital context map have different scales and acquisition times. Use the regional measurement table for quantitative comparison; neither view surveys a safe traverse or cave entrance.</p>
        </section>
        <section className="panel min-w-0 p-5" aria-labelledby="measurement-title">
          <h3 id="measurement-title" className="text-lg font-semibold text-white">What was actually compared?</h3>
          <p className="mt-2 text-sm leading-relaxed text-lunar-300">{study.measurements.sampling_note} Terrain comparison grid: <strong className="text-lunar-100">{study.measurements.comparison_grid_m} m</strong>; sampling radius: <strong className="text-lunar-100">{study.measurements.radius_m / 1000} km</strong> on each body. Resampling does not increase native detail.</p>
          <p className="mt-2 text-xs leading-relaxed text-lunar-300">Earth: Copernicus DEM GLO-30 ({study.measurements.earth_native_dem_m} m native). Planet: {study.measurements.planet_dem_product}. Earth valid terrain coverage: {n(study.measurements.earth_valid_fraction == null ? null : study.measurements.earth_valid_fraction * 100)}%. Climate inputs: CHELSA 1981–2010 (~1 km) and ERA5 1991–2020 (0.25°), modeled, not station measurements.</p>
          <div className="mt-4 overflow-x-auto" role="region" aria-label="Regional measurement comparison" tabIndex={0}>
            <table className="table-base min-w-[620px]"><thead><tr><th scope="col">Measurement</th><th scope="col">Earth</th><th scope="col">{study.reference.body}</th><th scope="col">Units / support</th></tr></thead><tbody>{study.measurements.metrics.map((m) => <tr key={m.label}><th scope="row" className="px-3 py-3 text-sm font-medium text-lunar-100">{m.label}</th><td className="font-mono">{n(m.earth)}</td><td className="font-mono">{n(m.planet)}</td><td className="max-w-xs text-xs"><span className="text-mars-300">{m.unit}</span><p className="mt-1 leading-relaxed text-lunar-300">{m.provenance}</p></td></tr>)}</tbody></table>
          </div>
          <p className="mt-3 text-xs text-lunar-300">— means unavailable; no value is imputed. Earth precipitation proxy: {n(study.measurements.earth_precipitation_mm_yr, 0)} mm/year. Permafrost probability proxy: {n(study.measurements.earth_permafrost_probability)} ({study.measurements.earth_permafrost_source}); not an ice concentration.</p>
          <p className="mt-2 text-xs text-lunar-400">Values exported from {study.measurements.source_files.join(" and ")}. Exported evidence includes full precision.</p>
        </section>
        <section className="panel min-w-0 p-5" aria-labelledby="benchmark-title">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><h3 id="benchmark-title" className="text-lg font-semibold text-white">Does it add value beyond the benchmarks?</h3><p className="mt-2 text-sm text-lunar-300">All four sites use {study.reference.name} and the same {study.objective_label} weights.</p></div><button className="btn" aria-pressed={stress} onClick={() => url.set({ stress: stress ? null : "1" })}>{stress ? "Restore baseline weights" : study.stress_label}</button></div>
          {study.exploratory_reference && <p className="mt-3 rounded-lg border border-amber-300/20 p-3 text-xs text-amber-100">Exploratory reference: this target is outside the profile's published reference set. These are live comparisons, not reproduced published profile scores.</p>}
          <p className="mt-3 text-sm leading-relaxed text-lunar-300">{study.stress_reason}</p>
          <div aria-live="polite" className="mt-4 overflow-x-auto" tabIndex={0} role="region" aria-label="Benchmark and stress test results">
            <table className="table-base min-w-[650px]"><thead><tr><th scope="col">Site</th><th scope="col">Score / 100</th><th scope="col">Full-catalog rank</th><th scope="col">Completeness</th><th scope="col">Missing-data bounds</th><th scope="col">Score change</th></tr></thead><tbody>{study.comparisons.map((row) => { const score = stress ? row.stress_result : row.result; return <tr key={row.site_id} className={row.candidate ? "bg-mars-500/5" : ""}><th scope="row" className="max-w-[220px] px-3 py-3 text-sm font-medium text-white">{row.name}<span className="mt-1 block text-xs font-normal text-lunar-300">{row.candidate ? "Case site" : "Challenge benchmark"}</span></th><td><span className="font-mono">{n(score.score, 1)}</span><div className="mt-1 w-20"><ScoreBar score={score.score} /></div></td><td>{score.rank ?? "—"}</td><td>{n(score.completeness * 100, 1)}%</td><td>{n(score.score_low, 1)}–{n(score.score_high, 1)}</td><td>{score.score == null || row.result.score == null ? "—" : n(score.score - row.result.score, 1)}</td></tr>; })}</tbody></table>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-lunar-300">{stress ? "Stress weights active. " : "Baseline weights active. "}{data.scoring_note} Missing-data bounds are not confidence intervals and omit uncertainty in proxy choice and input measurement.</p>
          <p className="mt-2 text-sm text-lunar-200">Baseline difference from the strongest of the three challenge benchmarks: <strong className="font-mono text-mars-300">{study.advantage_vs_best_benchmark == null ? "unavailable" : `${study.advantage_vs_best_benchmark > 0 ? "+" : ""}${n(study.advantage_vs_best_benchmark, 1)} points`}</strong>. A positive difference is an internal proxy-score advantage, not evidence of superior field performance.</p>
        </section>
        {study.strict_evidence && <StrictEvidencePanel data={study.strict_evidence} objective={study.objective} />}
        <div className="grid gap-4 lg:grid-cols-2"><section className="panel p-5"><h3 className="panel-title text-mars-300">Where the analogy breaks</h3><ul className="mt-3 list-disc space-y-3 pl-5 text-sm leading-relaxed text-lunar-200">{study.limits.map((l) => <li key={l}>{l}</li>)}</ul></section><section id="case-field-plan" className="panel p-5"><h3 className="panel-title text-signal-cyan">Proposed field-validation plan</h3><ol className="mt-3 list-decimal space-y-3 pl-5 text-sm leading-relaxed text-lunar-200">{study.field_plan.map((p) => <li key={p}>{p}</li>)}</ol><p className="mt-3 text-xs text-lunar-400">A proposed research protocol; no access permission, field work or hardware qualification is implied.</p></section></div>
        <section id="case-evidence" className="panel p-5"><h3 className="panel-title">Verified source trail</h3><ul className="mt-3 space-y-3">{study.sources.map((s) => <li key={s.url}><a className="link text-sm" href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a><p className="mt-1 text-xs leading-relaxed text-lunar-300">Supports: {s.supports}</p></li>)}</ul><p className="mt-4 text-xs text-lunar-300">This source review supplies context and caveats. It does not silently relabel the scoring inputs as primary measurements.</p></section>
        <div className="no-print flex flex-wrap gap-2">
          <Link className="btn btn-primary" href={`/compare?ids=${study.comparisons.map((r) => r.site_id).join(",")}&ref=${study.ref_id}&obj=${study.objective}`}>Open this case in Comparison Lab →</Link>
          <button className="btn" onClick={() => exportCase(study)}>Download evidence JSON</button>
          <button className="btn" onClick={() => downloadText(`terraanalog_${study.id}_measurements.csv`, toCSV(study.measurements.metrics.map((m) => ({ ...m, case_id: study.id, reference: study.ref_id, comparison_grid_m: study.measurements.comparison_grid_m, radius_m: study.measurements.radius_m }))))}>Measurements CSV</button>
          <button className="btn" onClick={() => window.print()}>Print case study</button>
          <button className="btn" onClick={async () => { try { await navigator.clipboard.writeText(`${window.location.origin}/science?case=${study.id}`); setCopied(true); } catch { setCopied(false); } }}>{copied ? "Link copied" : "Copy case link"}</button>
        </div>
      </article>
    </>}
  </div>;
}
