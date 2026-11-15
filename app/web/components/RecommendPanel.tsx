"use client";
import Link from "next/link";
import { useEffect, useRef, useState, useId } from "react";
import { apiPost, userErrorMessage } from "@/lib/api";
import { EXAMPLE_QUERIES } from "@/lib/constants";
import type { RecommendResponse } from "@/lib/types";
import { AnalogTypeChip, ErrorNote, ScoreBar } from "./ui";

export function RecommendPanel({ compact = false, onPick }: { compact?: boolean; onPick?: (siteId: string, refId: string, objective: string) => void }) {
  const inputId = useId();
  const titleId = useId();
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const [q, setQ] = useState("");
  const [res, setRes] = useState<RecommendResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (query: string) => {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setRes(null);
    setQ(query);
    setBusy(true);
    setErr(null);
    try {
      const result = await apiPost<RecommendResponse>("/recommend", { query, top_k: compact ? 3 : 5 }, request.signal);
      if (!request.signal.aborted) setRes(result);
    } catch (e) {
      if (!request.signal.aborted) setErr(userErrorMessage(e));
    } finally {
      if (!request.signal.aborted) setBusy(false);
    }
  };

  return (
    <section aria-labelledby={titleId} className="panel p-4" data-testid="recommend-panel">
      <h2 id={titleId} className="panel-title">Explainable recommendation engine</h2>
      <p className="mt-1 text-xs text-lunar-400">
        Plain-language intent → structured filters → documented scoring. Deterministic; no generative model invents sites, values or citations.
      </p>
      <form className="mt-3 flex flex-col gap-2 sm:flex-row" onSubmit={(e) => { e.preventDefault(); if (q.trim()) run(q.trim()); }}>
        <label htmlFor={inputId} className="sr-only">Describe your mission test</label>
        <input id={inputId} className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Find Earth environments suitable for testing lunar polar rovers" maxLength={500} />
        <button className="btn btn-primary shrink-0" type="submit" disabled={busy || !q.trim()}>{busy ? "Analysing…" : "Recommend"}</button>
      </form>
      <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Example queries">
        {EXAMPLE_QUERIES.slice(0, compact ? 3 : 5).map((ex) => (
          <button key={ex} className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-lunar-300 hover:border-mars-400/60 hover:text-white" disabled={busy} onClick={() => run(ex)}>{ex}</button>
        ))}
      </div>
      <div aria-live="polite" aria-busy={busy} className="mt-3">
        {busy && <p className="text-sm text-lunar-300" role="status">Comparing mission requirements with the research catalog…</p>}
        <ErrorNote error={err} />
        {res && (
          <div className="fade-in space-y-3">
            <div className="flex flex-wrap items-center gap-1.5 text-xs text-lunar-300">
              <span className="text-lunar-400">Interpreted as:</span>
              <span className="chip bg-white/5 ring-white/10">{res.interpretation.body === "moon" ? "☾ Moon" : "♂ Mars"}</span>
              <span className="chip bg-white/5 ring-white/10">ref: {res.interpretation.reference_name}</span>
              <span className="chip bg-mars-500/10 text-mars-300 ring-mars-400/30">{res.interpretation.objective_label}</span>
              {res.interpretation.analog_types.map((t) => <AnalogTypeChip key={t} type={t} />)}
            </div>
            {res.notes.map((n) => <p key={n} className="text-xs text-amber-200">{n}</p>)}
            <ol className="space-y-2">
              {res.results.map((r) => (
                <li key={r.site_id} className="rounded-lg border border-white/10 bg-space-900/50 p-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-mars-600/20 font-mono text-xs text-mars-300">#{r.rank}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-white">{r.name}</p>
                      <div className="mt-1 flex items-center gap-2"><div className="flex-1"><ScoreBar score={r.score} low={r.score_low} high={r.score_high} /></div><span className="font-mono text-xs">{r.score}</span></div>
                    </div>
                    {onPick ? (
                      <button className="btn text-xs" onClick={() => onPick(r.site_id, res.interpretation.ref_id, res.interpretation.objective)}>View</button>
                    ) : (
                      <Link className="btn text-xs" href={`/explorer?site=${r.site_id}&ref=${res.interpretation.ref_id}&obj=${res.interpretation.objective}`}>View</Link>
                    )}
                  </div>
                  {!compact && (
                    <div className="mt-2 space-y-1 text-xs text-lunar-200">
                      {r.why.map((w) => <p key={w}>• {w}</p>)}
                      {r.caveats.map((c) => <p key={c} className="text-amber-200/90">⚠ {c}</p>)}
                    </div>
                  )}
                </li>
              ))}
            </ol>
            {res.excluded_insufficient_evidence.length > 0 && (
              <p className="text-xs text-lunar-400">Not ranked (insufficient evidence): {res.excluded_insufficient_evidence.map((e) => e.site_id).join(", ")}</p>
            )}
            <div className="rounded-lg border border-mars-400/20 bg-mars-500/[0.05] p-3">
              <p className="text-xs font-semibold text-mars-300">What Earth cannot replicate for this {res.interpretation.body === "moon" ? "lunar" : "Martian"} test</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-lunar-200">
                {res.cannot_replicate_on_earth.slice(0, compact ? 3 : 6).map((c) => <li key={c}>{c}</li>)}
              </ul>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
