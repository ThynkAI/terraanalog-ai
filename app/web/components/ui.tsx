"use client";
import Link from "next/link";
import { ANALOG_TYPE_COLORS, VALUE_TYPE_STYLE } from "@/lib/constants";
import { scoreColor } from "@/lib/format";
import type { Body } from "@/lib/types";
import { useMeta } from "./MetaContext";

export function DataStatusBadge() {
  const { meta, loading } = useMeta();
  if (loading && !meta) return <span className="chip bg-white/5 text-lunar-300 ring-white/10">Loading data…</span>;
  if (!meta) return <span className="chip bg-red-500/15 text-red-200 ring-red-400/40">Data offline</span>;
  const s = meta.data_status;
  return (
    <Link
      href="/data"
      data-testid="data-status-badge"
      className={`chip ${s.synthetic ? "bg-pink-500/15 text-pink-200 ring-pink-400/40" : "bg-emerald-500/15 text-emerald-200 ring-emerald-400/40"}`}
      title={s.synthetic ? "All analog scores are synthetic/provisional placeholders" : "Research dataset loaded"}
    >
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${s.synthetic ? "bg-pink-300" : "bg-emerald-300"}`} />
      {s.label}
      {s.error_count > 0 && <span className="text-red-300">· {s.error_count} errors</span>}
    </Link>
  );
}

export function ValueTypeBadge({ type, compact = false }: { type: string; compact?: boolean }) {
  const s = VALUE_TYPE_STYLE[type] ?? VALUE_TYPE_STYLE.synthetic;
  return (
    <span className={`chip ${s.cls}`} title={s.desc}>
      {compact ? s.label.slice(0, 4) : s.label}
    </span>
  );
}

export function BodyBadge({ body }: { body: Body }) {
  return (
    <span className={`chip ${body === "moon" ? "bg-lunar-200/10 text-lunar-100 ring-lunar-300/40" : "bg-mars-500/15 text-mars-300 ring-mars-400/40"}`}>
      {body === "moon" ? "☾ Moon" : "♂ Mars"}
    </span>
  );
}

export function AnalogTypeChip({ type }: { type: string }) {
  const { meta } = useMeta();
  const c = ANALOG_TYPE_COLORS[type] ?? "#aab2bf";
  return (
    <span className="chip bg-white/[0.03] text-lunar-100 ring-white/10">
      <AnalogIcon type={type} size={12} />
      <span style={{ color: c }}>{meta?.analog_types[type] ?? type.replace(/_/g, " ")}</span>
    </span>
  );
}

/** Category symbols: shape encodes analog environment type (also used on map markers and the legend). */
export function AnalogIcon({ type, size = 16, color }: { type: string; size?: number; color?: string }) {
  const c = color ?? ANALOG_TYPE_COLORS[type] ?? "#aab2bf";
  const common = { width: size, height: size, viewBox: "0 0 20 20", "aria-hidden": true as const };
  switch (type) {
    case "polar_desert":
      return (<svg {...common}><path d="M10 2v16M3 6l14 8M17 6L3 14" stroke={c} strokeWidth="2" strokeLinecap="round" /></svg>);
    case "permafrost_ice":
      return (<svg {...common}><polygon points="10,2 17,6 17,14 10,18 3,14 3,6" fill="none" stroke={c} strokeWidth="2" /><circle cx="10" cy="10" r="2.5" fill={c} /></svg>);
    case "basaltic_volcanic":
      return (<svg {...common}><polygon points="10,3 18,17 2,17" fill={c} /></svg>);
    case "impact_crater":
      return (<svg {...common}><circle cx="10" cy="10" r="7" fill="none" stroke={c} strokeWidth="2.5" /><circle cx="10" cy="10" r="2" fill={c} /></svg>);
    case "lava_tube_cave":
      return (<svg {...common}><path d="M2 17V10a8 8 0 0 1 16 0v7h-4v-6a4 4 0 0 0-8 0v6z" fill={c} /></svg>);
    case "hyperarid_desert":
    case "arid_desert":
      return (<svg {...common}><circle cx="10" cy="7" r="3.5" fill={c} /><path d="M1 16c3-3 6-3 9 0s6 3 9 0" stroke={c} strokeWidth="2" fill="none" /></svg>);
    case "acidic_aqueous":
    case "aqueous_alteration":
      return (<svg {...common}><path d="M10 2C10 2 4 9 4 13a6 6 0 0 0 12 0c0-4-6-11-6-11z" fill={c} /></svg>);
    case "high_altitude":
      return (<svg {...common}><path d="M1 17l6-10 3 5 3-7 6 12z" fill={c} /></svg>);
    case "evaporite_basin":
      return (<svg {...common}><polygon points="10,2 18,10 10,18 2,10" fill="none" stroke={c} strokeWidth="2" /><polygon points="10,6.5 13.5,10 10,13.5 6.5,10" fill={c} /></svg>);
    default:
      return (<svg {...common}><rect x="4" y="4" width="12" height="12" fill={c} /></svg>);
  }
}

export function ScoreBar({ score, low, high, label }: { score: number | null | undefined; low?: number; high?: number; label?: string }) {
  const s = score ?? null;
  return (
    <div
      className="w-full"
      role={s === null ? "img" : "meter"}
      aria-valuemin={s === null ? undefined : 0}
      aria-valuemax={s === null ? undefined : 100}
      aria-valuenow={s === null ? undefined : s}
      aria-label={label ?? (s === null ? "no score: insufficient evidence" : `score ${s} of 100`)}
    >
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
        {low !== undefined && high !== undefined && high > low && (
          <div className="absolute inset-y-0 rounded-full bg-white/15" style={{ left: `${low}%`, width: `${high - low}%` }} title={`plausible range ${low}–${high}`} />
        )}
        {s !== null && <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${s}%`, background: scoreColor(s) }} />}
      </div>
    </div>
  );
}

export function Loading({ label = "Loading…", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-2">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-5 rounded" />
      ))}
    </div>
  );
}

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div role="alert" className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
      {error}
    </div>
  );
}

export function PageHeader({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-5 fade-in">
      {eyebrow && <p className="panel-title text-mars-300">{eyebrow}</p>}
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">{title}</h1>
      {children && <div className="mt-2 max-w-3xl text-sm leading-relaxed text-lunar-300">{children}</div>}
    </div>
  );
}

export function StatusPill({ status }: { status?: string }) {
  if (!status || status === "scored") return null;
  return (
    <span className="chip bg-slate-500/15 text-slate-300 ring-slate-400/40" title="Evidence completeness below threshold; no point score is shown">
      {status === "no_data" ? "No data" : "Insufficient evidence"}
    </span>
  );
}
