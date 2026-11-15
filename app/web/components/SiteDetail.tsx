"use client";
import Link from "next/link";
import { useState } from "react";
import { useApi } from "@/lib/api";
import { fmtLat, fmtLonEarth, num, pct } from "@/lib/format";
import type { SiteDetail as SiteDetailT } from "@/lib/types";
import { BreakdownBar } from "./Charts";
import { useMeta } from "./MetaContext";
import { AnalogTypeChip, BodyBadge, ErrorNote, Loading, ScoreBar, StatusPill, ValueTypeBadge } from "./ui";

export function EvidenceInspector({ detail }: { detail: SiteDetailT }) {
  const { meta } = useMeta();
  const [open, setOpen] = useState<string | null>(null);
  // Per-reference datasets: only the selected reference's criteria, labelled by feature. Fixture shape: all criteria.
  const crit = detail.active_criteria?.length
    ? detail.active_criteria.map((a) => ({ id: a.criterion_id, label: a.label, earth_proxy: a.earth_proxy || meta?.criteria.find((c) => c.id === a.criterion_id)?.earth_proxy || "" }))
    : (meta?.criteria ?? []).map((c) => ({ id: c.id, label: c.label, earth_proxy: c.earth_proxy }));
  return (
    <div>
      <h3 className="panel-title mb-2">Evidence inspector{detail.active_criteria?.length ? <span className="ml-1 normal-case tracking-normal text-lunar-400">· criteria for {detail.ref_id}</span> : null}</h3>
      <ul className="divide-y divide-white/5 rounded-lg border border-white/10">
        {crit.map((c) => {
          const fv = detail.features[c.id];
          const ev = detail.evidence[c.id] ?? [];
          const isOpen = open === c.id;
          return (
            <li key={c.id}>
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-white/[0.03]"
                aria-expanded={isOpen}
                aria-controls={`ev-${c.id}`}
                onClick={() => setOpen(isOpen ? null : c.id)}
              >
                <span className="flex-1 text-lunar-100">{c.label}</span>
                <span className="font-mono text-xs text-lunar-200" title={fv?.value == null ? "not available: see data gaps" : undefined}>{fv?.value ?? "—"}/5</span>
                <ValueTypeBadge type={fv?.value_type ?? "missing"} />
                <span aria-hidden="true" className="text-lunar-400">{isOpen ? "▾" : "▸"}</span>
              </button>
              {isOpen && (
                <div id={`ev-${c.id}`} className="space-y-2 bg-space-900/60 px-3 py-2 text-xs text-lunar-200">
                  <p><span className="text-lunar-400">Earth proxy:</span> {c.earth_proxy}</p>
                  <p><span className="text-lunar-400">Source ID:</span> <span className="font-mono">{fv?.source_id || "—"}</span> · <span className="text-lunar-400">confidence:</span> {fv?.confidence ?? "—"}</p>
                  {ev.length === 0 && <p className="italic text-lunar-400">No evidence record for this criterion.</p>}
                  {ev.map((e, i) => (
                    <div key={i} className={`rounded border p-2 ${e.value_type === "missing" ? "border-amber-400/30 bg-amber-500/5" : "border-white/10"}`}>
                      {e.value_type === "missing" && <p className="mb-1 text-[10px] uppercase tracking-wide text-amber-200/80">Explained gap</p>}
                      <p>{e.statement}</p>
                      <p className="mt-1 text-lunar-400">Citation: {e.citation}</p>
                    </div>
                  ))}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function SiteDetail({ siteId, refId, objective, weights, onClose, onCompare, inCompare }: {
  siteId: string; refId: string; objective: string; weights?: string; onClose?: () => void; onCompare?: (id: string) => void; inCompare?: boolean;
}) {
  const { data, error, loading, retry } = useApi<SiteDetailT>(`/sites/${encodeURIComponent(siteId)}`, { ref_id: refId, objective, weights });
  const [copied, setCopied] = useState(false);
  if (loading && !data) return <div className="p-4"><Loading rows={8} /></div>;
  if (error) return <div className="p-4"><ErrorNote error={error} /><button className="btn mt-2" onClick={retry}>Retry site evidence</button></div>;
  if (!data) return null;
  const s = data.score;
  const inScore = s?.breakdown.filter((b) => b.in_score !== false) ?? [];
  const separate = s?.breakdown.filter((b) => b.in_score === false) ?? [];
  const published = data.published_rankings.filter((p) => p.ref_id === refId && p.objective === objective);
  const copyLink = async () => {
    const url = `${window.location.origin}/explorer?site=${data.site_id}&ref=${refId}&obj=${objective}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      window.prompt("Copy this link", url);
    }
  };
  return (
    <article aria-labelledby="site-title" className="fade-in space-y-4 p-4" data-testid="site-detail">
      <header className="flex items-start gap-2">
        <div className="flex-1">
          <p className="font-mono text-[11px] text-lunar-400">{data.site_id} · {data.country}{data.region ? ` · ${data.region}` : ""}</p>
          <h2 id="site-title" className="text-lg font-semibold text-white">{data.name}</h2>
          <p className="mt-0.5 font-mono text-xs text-lunar-300">
            {fmtLat(data.lat)}, {fmtLonEarth(data.lon)} <span className="text-lunar-400">(WGS84)</span>
          </p>
        </div>
        {onClose && <button className="btn btn-ghost px-2" onClick={onClose} aria-label="Close site details">✕</button>}
      </header>

      <div className="flex flex-wrap gap-1.5">
        {data.target_bodies.map((b) => <BodyBadge key={b} body={b} />)}
        {data.analog_types.map((t) => <AnalogTypeChip key={t} type={t} />)}
        {data.climate_class ? <span className="chip bg-white/5 text-lunar-100 ring-white/15" title={data.climate_class_source || "Köppen–Geiger class"}>{data.climate_class}{data.aridity_class ? ` · ${data.aridity_class}` : ""}</span> : null}
        <span className="chip bg-pink-500/10 text-pink-200 ring-pink-400/30" title={data.score_status}>provenance: {data.provenance}</span>
      </div>

      {s && (
        <section className="rounded-lg border border-white/10 bg-space-900/50 p-3" aria-label="Analog score">
          <div className="flex items-baseline justify-between">
            <span className="text-xs text-lunar-300">Score vs selected reference</span>
            <StatusPill status={s.status} />
          </div>
          <div className="mt-1 flex items-end gap-3">
            <span className="text-3xl font-semibold text-white">{s.score ?? "—"}</span>
            <span className="pb-1 text-xs text-lunar-400">/100 · rank {s.rank ?? "unranked"} · range {s.score_low}–{s.score_high}</span>
          </div>
          <div className="mt-2"><ScoreBar score={s.score} low={s.score_low} high={s.score_high} /></div>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div><dt className="text-lunar-400">Evidence completeness</dt><dd className="font-medium text-lunar-100">{pct(s.completeness)}</dd></div>
            <div><dt className="text-lunar-400">Scientific confidence</dt><dd className="font-medium text-lunar-100">{pct(s.confidence)}</dd></div>
          </dl>
          <div className="mt-3"><BreakdownBar breakdown={s.breakdown} /></div>
          <table className="table-base mt-2 text-xs">
            <caption className="sr-only">Transparent score breakdown</caption>
            <thead><tr><th scope="col">Feature</th><th scope="col">Value</th><th scope="col">Weight</th><th scope="col">Points</th></tr></thead>
            <tbody>
              {inScore.map((b) => (
                <tr key={b.criterion_id} className={b.missing ? "opacity-60" : ""}>
                  <td>{b.label}</td>
                  <td className="whitespace-nowrap" title={b.value == null ? "not available: see data gaps" : undefined}>{b.value ?? "—"} <ValueTypeBadge type={b.value_type} compact /></td>
                  <td className="font-mono">{num(b.effective_weight, 2)}</td>
                  <td className="font-mono">{b.contribution ?? (b.missing ? "missing" : "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {separate.map((b) => (
            <div key={b.criterion_id} className="mt-2 rounded border border-white/10 px-2 py-1 text-xs text-lunar-200" data-testid="separate-criterion">
              <p>
                <span className="text-lunar-400">{b.label} — {b.criterion_id === "operational_suitability" || /operational/i.test(b.criterion_id) ? "shown separately, never added to the fidelity score" : "weight 0 under this objective, not in the score"}:</span>{" "}
                <span className="font-mono text-white">{b.value ?? "—"}/5</span> <ValueTypeBadge type={b.value_type} compact />
                {b.criterion_id === "operational_suitability" && b.confidence != null ? <span className="ml-1 text-lunar-300">· confidence {pct(b.confidence)}</span> : null}
              </p>
              {b.criterion_id === "operational_suitability" && data.operational_components ? (
                <p className="mt-1 text-[11px] text-lunar-400">Components: {Object.entries(data.operational_components).map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`).join(" · ")}</p>
              ) : null}
              {b.criterion_id === "operational_suitability" && data.operational_confidence_method ? (
                <p className="mt-1 text-[11px] text-lunar-400">{data.operational_confidence_method}</p>
              ) : null}
            </div>
          ))}
          {published.length > 0 && !weights && (
            <p className="mt-2 text-xs text-lunar-300" data-testid="published-score">
              Published research score for this reference &amp; objective: <span className="font-mono text-white">{published[0].score ?? "—"}</span>
              {published[0].rank ? ` (rank ${published[0].rank})` : ""} · live score reproduces it from the same values.
            </p>
          )}
          {s.trait_matches.length > 0 && <p className="mt-2 text-xs text-lunar-300">Shared traits with reference: {s.trait_matches.join(", ").replace(/_/g, " ")}</p>}
        </section>
      )}

      <section className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2" aria-label="Site characteristics">
        <div><h3 className="panel-title">Geology</h3><p className="mt-1 text-lunar-200">{data.geology || "—"}</p></div>
        <div>
          <h3 className="panel-title">Climate</h3>
          {(data.climate_class || data.aridity_class) ? (
            <p className="mt-1 text-lunar-200">
              <span className="font-medium text-white">Köppen–Geiger {data.climate_class || "—"}</span>
              {" · "}
              <span className="font-medium text-white">aridity {data.aridity_class || "—"}</span>
            </p>
          ) : null}
          {data.aridity_class === "humid" && data.climate_class && /^E/i.test(data.climate_class) ? (
            <p className="mt-1 text-[11px] text-lunar-400">Aridity is the UNEP P/ET0 class of the ERA5 grid cell. Cold polar sites can be classed “humid” even when they are dry in everyday terms, because evaporation is low.</p>
          ) : data.aridity_class ? (
            <p className="mt-1 text-[11px] text-lunar-400">Aridity is the UNEP P/ET0 class of the ERA5 grid cell, shown next to the Köppen–Geiger class because the two can disagree (for example a polar site classed humid).</p>
          ) : null}
          {data.climate_class_source ? <p className="mt-1 text-[11px] text-lunar-400">{data.climate_class_source}</p> : null}
          <p className="mt-1 text-lunar-200">{data.climate || "—"}</p>
        </div>
        <div className="sm:col-span-2">
          <h3 className="panel-title">Environmental characteristics</h3>
          <dl className="mt-1 grid grid-cols-1 gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
            {Object.entries(data.environment).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2 border-b border-white/5 py-0.5">
                <dt className="text-lunar-400">{k.replace(/_/g, " ")}</dt>
                <dd className={`text-right ${String(v).startsWith("pending") ? "italic text-lunar-400" : "text-lunar-100"}`}>{String(v)}</dd>
              </div>
            ))}
            <div className="flex justify-between gap-2 border-b border-white/5 py-0.5">
              <dt className="text-lunar-400">elevation (m)</dt>
              <dd className="italic text-lunar-400">{data.elevation_m ?? "not measured"}</dd>
            </div>
          </dl>
        </div>
        <div className="sm:col-span-2"><h3 className="panel-title">Mission use cases</h3>
          <p className="mt-1 text-lunar-200">{data.mission_objectives.filter((o) => o !== "general").map((o) => o.replace(/_/g, " ")).join(" · ") || "—"}</p>
        </div>
        <div className="sm:col-span-2"><h3 className="panel-title">Imagery</h3>
          {data.imagery ? (
            // eslint-disable-next-line @next/next/no-img-element
            <figure>
              <img src={data.imagery.url} alt={`${data.name} imagery`} className="mt-1 rounded" />
              <figcaption className="mt-1 text-xs text-lunar-400">
                {data.imagery.credit}
                {" · "}
                {data.imagery.license_url ? <a className="link" href={data.imagery.license_url} target="_blank" rel="noreferrer">{data.imagery.license}</a> : data.imagery.license}
                {data.imagery.attribution_page ? <>{" · "}<a className="link" href={data.imagery.attribution_page} target="_blank" rel="noreferrer">Source page</a></> : null}
                {data.imagery.source ? <span className="block text-lunar-500">{data.imagery.source}</span> : null}
              </figcaption>
            </figure>
          ) : (
            <p className="mt-1 text-xs italic text-lunar-400">No licensed imagery is supplied for this site in the dataset (Salar de Antofalla and the Dresser Formation have none). Use the satellite basemap layer (NASA GIBS) on the map.</p>
          )}
        </div>
      </section>

      <EvidenceInspector detail={data} />

      {data.reference_scores && (
        <section>
          <h3 className="panel-title mb-2">Scores against every planetary reference</h3>
          <ul className="space-y-1 text-xs">
            {data.reference_scores.filter((r) => r.body_relevant).map((r) => (
              <li key={r.ref_id} className="flex items-center gap-2">
                <span className="w-48 truncate text-lunar-200" title={r.name}>{r.name}</span>
                <div className="flex-1"><ScoreBar score={r.score} /></div>
                <span className="w-10 text-right font-mono text-lunar-100">{r.score ?? "—"}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.profile_rankings && data.profile_rankings.length > 0 && (
        <section>
          <h3 className="panel-title mb-2">Published profile rankings (research package)</h3>
          <p className="mb-2 text-[11px] text-lunar-400">Each mission profile takes the best matched reference. Monte Carlo intervals are from 2000 Dirichlet weight draws in the research export, not a live recompute.</p>
          <div className="overflow-x-auto">
            <table className="table-base text-xs">
              <thead><tr><th scope="col">Profile</th><th scope="col">Matched ref</th><th scope="col">Score</th><th scope="col">Rank</th><th scope="col">MC 5–95%</th><th scope="col">P(top 5)</th></tr></thead>
              <tbody>
                {data.profile_rankings.map((r) => (
                  <tr key={`${r.body}-${r.mission_profile}`}>
                    <td>{(r.mission_profile || "").replace(/_/g, " ")}</td>
                    <td className="font-mono">{r.matched_reference_id || "—"}</td>
                    <td className="font-mono">{r.fidelity_score ?? "—"}</td>
                    <td className="font-mono">{r.fidelity_rank ?? "—"}</td>
                    <td className="font-mono">{r.mc_score_p05 != null && r.mc_score_p95 != null ? `${r.mc_score_p05}–${r.mc_score_p95}` : "—"}</td>
                    <td className="font-mono">{r.mc_top5_probability != null ? pct(r.mc_top5_probability) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {data.data_gaps && (
        <section>
          <h3 className="panel-title mb-1">Documented data gaps</h3>
          <dl className="mt-1 space-y-1 text-xs text-lunar-200">
            {data.data_gaps.missing_numeric ? <div><dt className="text-lunar-400">Missing numeric inputs</dt><dd>{data.data_gaps.missing_numeric}</dd></div> : null}
            {data.data_gaps.hypothesized_tags ? <div><dt className="text-lunar-400">Hypothesized tags</dt><dd>{data.data_gaps.hypothesized_tags}</dd></div> : null}
            {data.data_gaps.permafrost_source ? <div><dt className="text-lunar-400">Permafrost source</dt><dd>{data.data_gaps.permafrost_source}</dd></div> : null}
            {data.data_gaps.recommended_field_measurements ? <div><dt className="text-lunar-400">Recommended field measurements</dt><dd>{data.data_gaps.recommended_field_measurements}</dd></div> : null}
          </dl>
        </section>
      )}

      <section>
        <h3 className="panel-title mb-1">Limitations — what Earth cannot replicate</h3>
        <ul className="list-disc space-y-0.5 pl-5 text-xs text-lunar-300">
          {Object.entries(data.cannot_replicate_on_earth ?? {}).flatMap(([b, items]) => (items ?? []).slice(0, 4).map((i) => <li key={b + i}><span className="text-lunar-400">{b}:</span> {i}</li>))}
          {data.limitations.map((l) => <li key={l} className={l.toLowerCase().includes("synthetic") ? "text-pink-200" : ""}>{l}</li>)}
        </ul>
        <p className="mt-2 text-xs text-lunar-400">Citations: {(data.citations ?? ["citation pending from research dataset"]).join("; ")}</p>
      </section>

      <div className="no-print flex flex-wrap gap-2">
        {onCompare && <button className="btn btn-primary" onClick={() => onCompare(data.site_id)} aria-pressed={inCompare}>{inCompare ? "✓ In comparison" : "+ Add to comparison"}</button>}
        <button className="btn" onClick={copyLink}>{copied ? "Link copied" : "Copy deep link"}</button>
        <Link className="btn" href={`/compare?ids=${data.site_id}&ref=${refId}&obj=${objective}`}>Open in Comparison Lab</Link>
      </div>
    </article>
  );
}
