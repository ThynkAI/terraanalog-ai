"use client";
import Link from "next/link";
import type { StrictEvidence } from "@/lib/science";

export function StrictEvidencePanel({ data, objective }: { data: StrictEvidence; objective: string }) {
  return <section className="rounded-xl border border-signal-cyan/20 bg-signal-cyan/[0.03] p-4" aria-label="Published evidence-strict check">
    <h3 className="text-sm font-semibold text-white">Does the shortlist survive stricter evidence?</h3>
    <p className="mt-2 text-xs leading-relaxed text-lunar-200">The research pipeline removes hypothesized categorical tags and reranks the mission profile. Literature-supported tags and numeric proxies remain; “strict” does not mean measured-only or field-validated.</p>
    <p className="mt-2 text-xs leading-relaxed text-lunar-300">{data.scope}</p>
    <div className="mt-3 grid grid-cols-2 gap-3 text-sm"><p>Rank agreement (Spearman ρ)<strong className="block font-mono text-signal-cyan">{data.spearman_strict_vs_base}</strong></p><p>Largest rank shift<strong className="block font-mono text-mars-300">{data.max_rank_shift} places</strong></p></div>
    <div className="mt-4 grid gap-4 sm:grid-cols-2">
      {(["base", "strict"] as const).map((mode) => <div key={mode}><h4 className="panel-title">{mode === "base" ? "Original top five" : "Evidence-strict top five"}</h4><ol className="mt-2 space-y-2 text-xs">
        {data[mode === "base" ? "top5_base" : "top5_strict"].map((id, i) => <li key={id} className="flex gap-2"><span className="font-mono text-lunar-400">{i + 1}.</span><Link href={`/explorer?site=${id}&ref=${data.references[0]}&obj=${objective}`} className="text-lunar-100 underline decoration-white/20 underline-offset-2">{data[mode === "base" ? "top5_base_names" : "top5_strict_names"][i]}</Link></li>)}
      </ol></div>)}
    </div>
    <p className="mt-3 text-[11px] text-lunar-400">Published references: {data.references.join(", ")}. Rank agreement measures stability, not scientific accuracy. Site links open the ordinary inspector against the first published reference.</p>
  </section>;
}
