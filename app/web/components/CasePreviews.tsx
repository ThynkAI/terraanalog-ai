"use client";
import Link from "next/link";
import { useState } from "react";
import type { Site } from "@/lib/types";

const CASES = [
  { id: "holuhraun-mobility", site: "EA-006", tag: "MARS / MOBILITY", title: "A volcanic field. A rover test.", place: "Holuhraun, Iceland", detail: "Investigate the terrain match to Elysium, then remove slope and ruggedness from the score." },
  { id: "undara-cave-robotics", site: "EA-016", tag: "MOON / CAVE ROBOTICS", title: "Below the surface, beyond the proxy.", place: "Undara, Australia", detail: "Explore basaltic caves and test the comparison without the temperature proxy." },
  { id: "svalbard-polar-prospecting", site: "EA-005", tag: "MOON / POLAR OPERATIONS", title: "Cold ground. Clear limitations.", place: "Bockfjorden, Svalbard", detail: "See why a polar research site can rank below Haughton and still inform a focused field exercise." },
];
function Preview({ item, site }: { item: typeof CASES[number]; site?: Site }) {
  const [failed, setFailed] = useState(false);
  const img = site?.imagery;
  return <article className="case-preview min-w-0 overflow-hidden rounded-xl border border-white/10 bg-space-900">
    <div className="relative h-48 overflow-hidden bg-space-800">
      {img && !failed ? <img src={img.url} alt={`${item.place}, archival geographic context`} loading="lazy" onError={() => setFailed(true)} className="h-full w-full object-cover" /> : <div className="case-landscape flex h-full items-center justify-center font-mono text-xs tracking-widest text-lunar-200">{item.place.toUpperCase()}</div>}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-space-950/90 via-transparent to-transparent" />
      <p className="absolute bottom-3 left-4 font-mono text-[10px] tracking-widest text-white">{item.tag}</p>
    </div>
    <div className="p-5"><p className="text-xs text-signal-cyan">{item.place}</p><h3 className="mt-2 text-lg font-medium text-white">{item.title}</h3><p className="mt-3 text-sm leading-relaxed text-lunar-300">{item.detail}</p><Link href={`/science?case=${item.id}`} className="mt-5 inline-flex min-h-10 items-center gap-2 text-sm font-medium text-mars-300 underline decoration-mars-500/30 underline-offset-4">Investigate this case <span aria-hidden="true">↗</span><span className="sr-only">: {item.place}</span></Link>
      {img && <p className="mt-3 text-[10px] leading-relaxed text-lunar-400">Archival context; conditions may differ today. <a href={img.attribution_page || img.url} className="underline underline-offset-2" target="_blank" rel="noreferrer">{img.credit}</a></p>}
    </div>
  </article>;
}
export function CasePreviews({ sites }: { sites: Site[] }) {
  return <section aria-labelledby="featured-cases">
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3"><div><p className="panel-title text-signal-cyan">Science in practice</p><h2 id="featured-cases" className="mt-2 text-2xl font-semibold tracking-tight text-white">Three places. Three research decisions.</h2><p className="mt-2 max-w-2xl text-sm leading-relaxed text-lunar-300">Compare real measurements, challenge a score, and see what the next field campaign would need to establish.</p></div><Link href="/science" className="link text-sm">All scientific case studies ↗</Link></div>
    <div className="grid gap-4 md:grid-cols-3">{CASES.map((item) => <Preview key={item.id} item={item} site={sites.find((s) => s.site_id === item.site)} />)}</div>
  </section>;
}
