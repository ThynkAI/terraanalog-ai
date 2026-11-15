"use client";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { CasePreviews } from "@/components/CasePreviews";
import { MissionLaunch } from "@/components/MissionLaunch";
import { useApi } from "@/lib/api";
import type { Site, RankingsResponse } from "@/lib/types";
import { useMeta } from "@/components/MetaContext";
import { RecommendPanel } from "@/components/RecommendPanel";
import { Loading, ScoreBar } from "@/components/ui";

const EarthMap = dynamic(() => import("@/components/EarthMap"), { ssr: false, loading: () => <div className="skeleton h-full" /> });

function Stat({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="border-l border-white/10 px-4 py-2 sm:px-6">
      <p className="text-3xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs uppercase tracking-wider text-lunar-300">{label}</p>
      {sub && <p className="mt-1 text-[11px] text-lunar-400">{sub}</p>}
    </div>
  );
}

function TopList({ refId, title, accent }: { refId: string; title: string; accent: string }) {
  const { data, error, loading, retry } = useApi<RankingsResponse>("/rankings", { ref_id: refId });
  return (
    <section className="panel p-4" aria-label={title}>
      <h3 className="panel-title" style={{ color: accent }}>{title}</h3>
      {error ? <p className="mt-3 text-sm text-lunar-300">Rankings unavailable. <button className="link" onClick={retry}>Try again</button></p> : loading && !data ? <div className="mt-3"><Loading rows={4} /></div> : (
        <ol className="mt-3 space-y-2">
          {(data?.rankings ?? []).filter((r) => r.rank).slice(0, 4).map((r) => (
            <li key={r.site_id} className="flex items-center gap-2 text-sm">
              <span className="w-5 font-mono text-xs text-lunar-400">{r.rank}</span>
              <Link href={`/explorer?site=${r.site_id}&ref=${refId}`} className="min-w-0 flex-1 truncate text-lunar-50 hover:text-mars-300">{r.name.split(" (")[0]}</Link>
              <div className="w-16 shrink-0 sm:w-24"><ScoreBar score={r.score} low={r.score_low} high={r.score_high} /></div>
              <span className="w-9 text-right font-mono text-xs">{r.score}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default function OverviewClient() {
  const { meta, refs } = useMeta();
  const c = meta?.data_status.counts;
  const router = useRouter();
  const { data: catalog } = useApi<{ sites: Site[] }>(meta ? "/sites" : null);
  return (
    <div className="space-y-6">
      <section className="mission-hero">
        <div className="relative z-10 px-6 py-10 sm:px-10 sm:py-14 lg:max-w-[58%] lg:py-20">
          <p className="panel-title text-signal-cyan">Terrestrial analog intelligence / 2026</p>
          <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-[1.08] tracking-tight text-white sm:text-6xl">
            Earth as a testbed<br />for the <span className="text-lunar-200">Moon</span><br />and <span className="text-mars-400">Mars.</span>
          </h1>
          <p className="mt-6 max-w-lg text-sm leading-relaxed text-lunar-200 sm:text-base">
            Before the next giant leap, find the right place to test it. Explore Earth environments that share the terrain, geology, and processes of other worlds.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link href="/explorer" className="btn btn-primary px-5 py-3">Explore Earth analogs <span aria-hidden="true">↗</span></Link>
            <Link href="/compare" className="btn bg-space-950/70 px-5 py-3">Comparison Lab</Link>
          </div>
          <p className="mt-5 font-mono text-[11px] text-lunar-300">OPEN DATA · TRACEABLE EVIDENCE · EXPLAINABLE SCORES</p>
        </div>
        <div className="hero-globe" role="region" aria-label="Earth analog site preview">
          <EarthMap sites={catalog?.sites ?? []} onSelect={(id) => router.push(`/explorer?site=${id}`)} label="Earth analog site preview" />
          <div className="pointer-events-none absolute bottom-12 left-5 right-5 flex items-center justify-between border-t border-white/15 pt-3 font-mono text-[10px] tracking-widest text-lunar-200">
            <span>EARTH / WGS84</span><span>SELECT A SITE TO INVESTIGATE ↗</span>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-y-5 py-3 md:grid-cols-4">
        <Stat label="Earth analog sites" value={c?.earth_sites ?? "–"} sub="WGS84 GeoJSON" />
        <Stat label="Planetary references" value={c?.planetary_references ?? "–"} sub="IAU/USGS Gazetteer coordinates" />
        <Stat label="Scoring features" value={meta ? (meta.features?.filter((f) => f.in_fidelity_score).length || meta.criteria.length) : "–"} sub={meta?.criteria_mode === "per_reference" ? `per reference · ${meta.criteria.length} criteria` : "transparent, weighted"} />
        <Stat label="Mission objectives" value={meta ? meta.objectives.filter((o) => o.id !== "general").length : "–"} sub={meta ? Array.from(new Set(meta.objectives.filter((o) => o.id !== "general").map((o) => o.label.replace(/^(Moon|Mars) /, "")))).slice(0, 6).join(" · ") : ""} />
      </div>

      <MissionLaunch />
      <CasePreviews sites={catalog?.sites ?? []} />

      <section className="panel grid gap-5 p-5 sm:grid-cols-[1fr_auto] sm:items-center" aria-labelledby="discovery-title">
        <div><p className="panel-title text-mars-300">Beyond the challenge benchmarks</p>
          <h2 id="discovery-title" className="mt-2 text-xl font-semibold text-white">Investigate the research candidates</h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-lunar-300">Go beyond Atacama, Haughton, and Death Valley. Explore {catalog ? catalog.sites.filter((s) => s.group === "candidate").length : "the"} candidate sites in the curated catalog, inspect their data gaps, and decide what needs field measurement. These are research leads; novelty and suitability require further validation.</p>
        </div>
        <Link href="/explorer?group=candidate" className="btn btn-primary whitespace-nowrap">Explore candidates →</Link>
      </section>

      <section className="grid gap-5 rounded-xl border border-signal-cyan/20 bg-signal-cyan/[0.03] p-5 sm:grid-cols-[1fr_auto] sm:items-center" aria-label="How to interpret an analog">
        <div><h2 className="text-sm font-semibold text-white">A shared process. A useful test. A different world.</h2>
        <p className="mt-2 max-w-4xl text-sm leading-relaxed text-lunar-300">Analog scores compare specific surface characteristics for a mission objective. Check evidence completeness alongside the score; access and operational suitability are assessed separately. Earth cannot reproduce planetary gravity, atmosphere, or radiation.</p></div>
        <Link href="/data" className="btn whitespace-nowrap">Inspect the evidence →</Link>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-7"><RecommendPanel /></div>
        <div className="space-y-4 lg:col-span-5">
          {(["moon", "mars"] as const).map((b) => {
            const id = meta?.default_reference[b];
            const r = refs.find((x) => x.ref_id === id);
            return id ? <TopList key={b} refId={id} title={`Top matches · ${(r?.name ?? id).split(" (")[0]}`} accent={b === "moon" ? "#c9ced6" : "#f08a55"} /> : null;
          })}
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
