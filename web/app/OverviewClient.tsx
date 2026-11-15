"use client";
import Link from "next/link";
import { useApi } from "@/lib/api";
import type { RankingsResponse } from "@/lib/types";
import { useMeta } from "@/components/MetaContext";
import { RecommendPanel } from "@/components/RecommendPanel";
import { Loading, ScoreBar } from "@/components/ui";

function Stat({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="panel p-4">
      <p className="text-3xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs uppercase tracking-wider text-lunar-300">{label}</p>
      {sub && <p className="mt-1 text-[11px] text-lunar-400">{sub}</p>}
    </div>
  );
}

function TopList({ refId, title, accent }: { refId: string; title: string; accent: string }) {
  const { data, loading } = useApi<RankingsResponse>("/rankings", { ref_id: refId });
  return (
    <section className="panel p-4" aria-label={title}>
      <h3 className="panel-title" style={{ color: accent }}>{title}</h3>
      {loading && !data ? <div className="mt-3"><Loading rows={4} /></div> : (
        <ol className="mt-3 space-y-2">
          {(data?.rankings ?? []).filter((r) => r.rank).slice(0, 4).map((r) => (
            <li key={r.site_id} className="flex items-center gap-2 text-sm">
              <span className="w-5 font-mono text-xs text-lunar-400">{r.rank}</span>
              <Link href={`/explorer?site=${r.site_id}&ref=${refId}`} className="w-44 truncate text-lunar-50 hover:text-mars-300">{r.name.split(" (")[0]}</Link>
              <div className="flex-1"><ScoreBar score={r.score} low={r.score_low} high={r.score_high} /></div>
              <span className="w-9 text-right font-mono text-xs">{r.score}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default function OverviewClient() {
  const { meta } = useMeta();
  const c = meta?.data_status.counts;
  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-2xl border border-white/[0.07] bg-gradient-to-br from-space-800 via-space-900 to-space-950 p-6 sm:p-10">
        <div aria-hidden="true" className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-gradient-to-br from-mars-400/30 to-mars-700/10 blur-2xl" />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-28 right-40 h-56 w-56 rounded-full bg-gradient-to-br from-lunar-200/20 to-lunar-500/5 blur-2xl" />
        <p className="panel-title text-mars-300">NASA Space Apps Challenge 2026 · Mission Overview</p>
        <h1 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight tracking-tight text-white sm:text-5xl">
          Earth as a testbed for the <span className="text-lunar-200">Moon</span> and <span className="text-mars-400">Mars</span>.
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-lunar-300 sm:text-base">
          TerraAnalog AI turns geospatial and planetary-science evidence into a decision-support tool: pick a lunar or Martian reference region and a
          mission objective, and see which Earth field sites best stand in for it — with a transparent score, evidence trail, uncertainty, and an
          honest list of what Earth cannot replicate.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Link href="/explorer" className="btn btn-primary">Open Earth Analog Explorer →</Link>
          <Link href="/moon" className="btn">☾ Moon references</Link>
          <Link href="/mars" className="btn">♂ Mars references</Link>
          <Link href="/compare" className="btn">Comparison Lab</Link>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Earth analog sites" value={c?.earth_sites ?? "–"} sub="WGS84 GeoJSON" />
        <Stat label="Planetary references" value={c?.planetary_references ?? "–"} sub="IAU/USGS Gazetteer coordinates" />
        <Stat label="Scoring criteria" value={meta?.criteria.length ?? "–"} sub="transparent, weighted" />
        <Stat label="Mission objectives" value={meta ? meta.objectives.length - 1 : "–"} sub="rover · drilling · ISRU · habitat · caves · EVA" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-7"><RecommendPanel /></div>
        <div className="space-y-4 lg:col-span-5">
          <TopList refId="moon-shackleton" title="Top matches · Shackleton crater vicinity" accent="#c9ced6" />
          <TopList refId="mars-jezero" title="Top matches · Jezero crater" accent="#f08a55" />
          <section className="panel p-4">
            <h3 className="panel-title">How it works</h3>
            <ol className="mt-2 space-y-2 text-sm text-lunar-200">
              <li><span className="font-mono text-mars-300">01</span> Select a planetary reference (real Gazetteer coordinates).</li>
              <li><span className="font-mono text-mars-300">02</span> Choose a mission objective — weights adapt transparently.</li>
              <li><span className="font-mono text-mars-300">03</span> Inspect score, completeness, confidence and every piece of evidence.</li>
              <li><span className="font-mono text-mars-300">04</span> Compare, stress-test weights, export a report, share a deep link.</li>
            </ol>
          </section>
        </div>
      </div>
    </div>
  );
}
