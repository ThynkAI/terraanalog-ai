"use client";
import { useMeta } from "./MetaContext";
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

export function ObjectiveSelect({ value, onChange, id = "objective-select" }: { value: string; onChange: (v: string) => void; id?: string }) {
  const { meta } = useMeta();
  return (
    <div>
      <label htmlFor={id} className="label">Mission objective</label>
      <select id={id} className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        {(meta?.objectives ?? []).map((o) => (
          <option key={o.id} value={o.id}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}
