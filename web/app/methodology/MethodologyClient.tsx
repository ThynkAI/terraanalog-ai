"use client";
import { useEffect, useState } from "react";
import { useMeta } from "@/components/MetaContext";
import { Markdown } from "@/components/Markdown";
import { ErrorNote, Loading, PageHeader, ValueTypeBadge } from "@/components/ui";

export default function MethodologyClient() {
  const { meta, refs } = useMeta();
  const [md, setMd] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetch("/api/docs/methodology").then(async (r) => (r.ok ? setMd(await r.text()) : setErr("Methodology document not available in the data directory."))).catch(() => setErr("Data service unavailable"));
  }, []);
  const crit = meta?.criteria ?? [];
  return (
    <div>
      <PageHeader eyebrow="Transparent & reproducible" title="Scientific Methodology">
        The narrative below is loaded from <code>scientific_methodology.md</code> in the active data directory; the tables are rendered live from <code>scoring_config.json</code>, so they always match the scores you see.
      </PageHeader>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <section className="panel p-5 xl:col-span-7" aria-label="Methodology document">
          <ErrorNote error={err} />
          {md === null && !err ? <Loading rows={10} /> : md && <Markdown text={md} />}
        </section>
        <div className="space-y-4 xl:col-span-5">
          <section className="panel overflow-x-auto p-4" aria-labelledby="bw-h">
            <h2 id="bw-h" className="panel-title mb-2">Body weights (live config)</h2>
            <table className="table-base text-xs">
              <thead><tr><th scope="col">Criterion</th><th scope="col">Moon</th><th scope="col">Mars</th><th scope="col">Earth proxy</th></tr></thead>
              <tbody>
                {crit.map((c) => (
                  <tr key={c.id}><th scope="row" className="text-left font-normal">{c.label}</th><td className="font-mono">{meta?.body_weights.moon[c.id] ?? "—"}</td><td className="font-mono">{meta?.body_weights.mars[c.id] ?? "—"}</td><td className="text-lunar-300">{c.earth_proxy}</td></tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="panel overflow-x-auto p-4" aria-labelledby="ow-h">
            <h2 id="ow-h" className="panel-title mb-2">Mission-objective multipliers</h2>
            <table className="table-base text-xs">
              <thead><tr><th scope="col">Objective</th><th scope="col">Multipliers</th></tr></thead>
              <tbody>
                {(meta?.objectives ?? []).map((o) => (
                  <tr key={o.id}><th scope="row" className="text-left font-normal">{o.label}</th><td className="text-lunar-300">{Object.entries(o.multipliers).map(([k, v]) => `${crit.find((c) => c.id === k)?.label ?? k} ×${v}`).join(", ") || "none (body weights only)"}</td></tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="panel overflow-x-auto p-4" aria-labelledby="rw-h">
            <h2 id="rw-h" className="panel-title mb-2">Reference multipliers</h2>
            <table className="table-base text-xs">
              <thead><tr><th scope="col">Reference</th><th scope="col">Multipliers</th></tr></thead>
              <tbody>
                {refs.map((r) => (
                  <tr key={r.ref_id}><th scope="row" className="text-left font-normal">{r.name}</th><td className="text-lunar-300">{Object.entries(meta?.reference_multipliers[r.ref_id] ?? {}).map(([k, v]) => `${k} ×${v}`).join(", ") || "—"}</td></tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="panel p-4" aria-labelledby="vt-h">
            <h2 id="vt-h" className="panel-title mb-2">Value types &amp; default confidence</h2>
            <ul className="space-y-1 text-xs">
              {Object.entries(meta?.value_type_confidence ?? {}).map(([k, v]) => (
                <li key={k} className="flex items-center gap-2"><ValueTypeBadge type={k} /><span className="font-mono text-lunar-200">{v}</span></li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-lunar-400">Minimum evidence completeness for a point score: <span className="font-mono text-white">{meta?.min_completeness}</span></p>
          </section>
        </div>
      </div>
    </div>
  );
}
