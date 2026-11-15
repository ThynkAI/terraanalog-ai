"use client";
import { useMeta, useObjectivesFor } from "./MetaContext";
import type { Body } from "@/lib/types";

export function ReferenceSelect({ value, onChange, body, id = "ref-select", label = "Planetary reference" }: { value: string; onChange: (v: string) => void; body?: Body; id?: string; label?: string }) {
  const { refs } = useMeta();
  const groups: Body[] = body ? [body] : ["moon", "mars"];
  return (
    <div>
      <label htmlFor={id} className="label">{label}</label>
      <select id={id} className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        {groups.map((b) => (
          <optgroup key={b} label={b === "moon" ? "Moon" : "Mars"}>
            {refs.filter((r) => r.body === b).map((r) => (
              <option key={r.ref_id} value={r.ref_id}>{r.name}</option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}

export function ObjectiveSelect({ value, onChange, id = "objective-select", body }: { value: string; onChange: (v: string) => void; id?: string; body?: Body | null }) {
  const objectives = useObjectivesFor(body);
  return (
    <div>
      <label htmlFor={id} className="label">Mission objective</label>
      <select id={id} className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        {objectives.map((o) => (
          <option key={o.id} value={o.id}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

/** Plain-language notes returned by the API (default reference used, objective/body mismatch, …). */
export function RefNotes({ notes, className = "" }: { notes?: string[]; className?: string }) {
  if (!notes?.length) return null;
  return (
    <div role="note" data-testid="ref-notes" className={`rounded border border-sky-400/25 bg-sky-500/[0.07] px-3 py-1.5 text-xs text-sky-100 ${className}`}>
      <ul className="space-y-0.5">{notes.map((n) => <li key={n}>ℹ {n}</li>)}</ul>
    </div>
  );
}
