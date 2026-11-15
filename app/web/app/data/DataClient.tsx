"use client";
import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import type { DatasetEntry } from "@/lib/types";
import { Markdown } from "@/components/Markdown";
import { useMeta } from "@/components/MetaContext";
import { ErrorNote, Loading, PageHeader, ValueTypeBadge } from "@/components/ui";

const STATUS_CLS: Record<string, string> = {
  ok: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/40",
  partial: "bg-amber-500/15 text-amber-300 ring-amber-400/40",
  invalid: "bg-red-500/15 text-red-300 ring-red-400/40",
  missing: "bg-slate-500/15 text-slate-300 ring-slate-400/40",
};

export default function DataClient() {
  const { meta } = useMeta();
  const ds = useApi<{ datasets: DatasetEntry[] }>("/datasets");
  const [refsMd, setRefsMd] = useState<string | null>(null);
  useEffect(() => {
    fetch("/api/docs/references").then(async (r) => setRefsMd(r.ok ? await r.text() : "")).catch(() => setRefsMd(""));
  }, []);
  const s = meta?.data_status;
  return (
    <div>
      <PageHeader eyebrow="Traceability" title="Data Sources and Provenance">
        Every value in TerraAnalog carries a value type (measured, modeled, provisional, synthetic or missing), a source ID and a citation slot.
        This page shows exactly which contract files are loaded, whether they validate, and where each dataset comes from.
      </PageHeader>
      {!s ? <Loading rows={6} /> : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          <section className="panel p-4 xl:col-span-5" aria-labelledby="files-h">
            <h2 id="files-h" className="panel-title mb-2">Data contract files</h2>
            <div className={`mb-3 rounded-lg px-3 py-2 text-sm ${s.synthetic ? "bg-pink-500/10 text-pink-100 ring-1 ring-pink-400/30" : "bg-emerald-500/10 text-emerald-100 ring-1 ring-emerald-400/30"}`}>
              {s.synthetic
                ? "Running on SYNTHETIC FIXTURES. The research bot's files have not been loaded yet. Set TERRA_DATA_DIR to their folder — no UI changes needed."
                : "Research dataset loaded."}
            </div>
            <table className="table-base text-xs">
              <thead><tr><th scope="col">File</th><th scope="col">Status</th></tr></thead>
              <tbody>
                {Object.entries(s.files).map(([f, st]) => (
                  <tr key={f}><td className="font-mono">{f}</td><td><span className={`chip ${STATUS_CLS[st] ?? ""}`}>{st}</span></td></tr>
                ))}
              </tbody>
            </table>
            <h3 className="panel-title mb-1 mt-4">Value-type inventory</h3>
            <ul className="flex flex-wrap gap-2 text-xs">
              {Object.entries(s.value_types).map(([k, v]) => <li key={k} className="flex items-center gap-1"><ValueTypeBadge type={k} /><span className="font-mono">{v}</span></li>)}
            </ul>
            <h3 className="panel-title mb-1 mt-4">Validation &amp; ID-consistency report</h3>
            <p className="text-xs text-lunar-300">{s.error_count} errors · {s.warning_count} warnings</p>
            <ul className="mt-1 max-h-48 space-y-1 overflow-y-auto text-xs">
              {s.issues.length === 0 && <li className="text-emerald-300">All site IDs, reference IDs, criteria and source IDs are consistent across files.</li>}
              {s.issues.map((i, n) => <li key={n} className={i.level === "error" ? "text-red-300" : "text-amber-200"}>[{i.level}] {i.file}: {i.message}</li>)}
            </ul>
          </section>
          <section className="panel overflow-x-auto p-4 xl:col-span-7" aria-labelledby="cat-h">
            <h2 id="cat-h" className="panel-title mb-2">Dataset catalog</h2>
            <ErrorNote error={ds.error} />
            <table className="table-base min-w-[640px] text-xs">
              <thead><tr><th scope="col">ID</th><th scope="col">Dataset</th><th scope="col">Licence</th><th scope="col">Use</th><th scope="col">Status</th></tr></thead>
              <tbody>
                {(ds.data?.datasets ?? []).map((d) => (
                  <tr key={d.source_id}>
                    <td className="font-mono">{d.source_id}</td>
                    <td>{d.url ? <a className="link" href={d.url.startsWith("http") ? d.url : undefined} target="_blank" rel="noreferrer">{d.name}</a> : d.name}<div className="text-lunar-400">{d.provider}</div></td>
                    <td className="text-lunar-300">{d.license}</td>
                    <td className="text-lunar-300">{d.usage}</td>
                    <td><span className={`chip ${d.status.startsWith("used") ? "bg-emerald-500/10 text-emerald-200 ring-emerald-400/30" : "bg-white/5 text-lunar-300 ring-white/10"}`}>{d.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="panel p-5 xl:col-span-12" aria-label="Source references">
            {refsMd === null ? <Loading rows={4} /> : refsMd ? <Markdown text={refsMd} /> : <p className="text-sm text-lunar-400">source_references.md not available.</p>}
          </section>
        </div>
      )}
    </div>
  );
}
