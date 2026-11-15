"use client";
import { useState } from "react";
import { ANALOG_TYPE_COLORS } from "@/lib/constants";
import { useMeta } from "./MetaContext";
import { AnalogIcon } from "./ui";

const RAMP = [
  { c: "#4ade80", l: "≥ 80" },
  { c: "#a3e635", l: "65–79" },
  { c: "#fbbf24", l: "50–64" },
  { c: "#f08a55", l: "35–49" },
  { c: "#ef4444", l: "< 35" },
  { c: "#6c7587", l: "no score" },
];

export function MapLegend() {
  const { meta } = useMeta();
  const [open, setOpen] = useState(true);
  return (
    <section aria-labelledby="legend-h" className="panel p-3 text-xs">
      <div className="flex items-center justify-between">
        <h2 id="legend-h" className="panel-title">Map legend</h2>
        <button className="btn btn-ghost px-1.5 py-0.5 text-xs" aria-expanded={open} aria-controls="legend-body" onClick={() => setOpen((o) => !o)}>
          {open ? "Hide" : "Show"}
        </button>
      </div>
      {open && (
        <div id="legend-body" className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <p className="mb-1 text-lunar-400">Symbol = primary analog type</p>
            <ul className="space-y-1">
              {Object.keys(ANALOG_TYPE_COLORS).map((t) => (
                <li key={t} className="flex items-center gap-2">
                  <AnalogIcon type={t} size={14} />
                  <span className="text-lunar-200">{meta?.analog_types[t] ?? t}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-1 text-lunar-400">Ring colour = analog score (0–100)</p>
            <ul className="space-y-1">
              {RAMP.map((r) => (
                <li key={r.l} className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded-full border-2" style={{ borderColor: r.c }} aria-hidden="true" />
                  <span className="text-lunar-200">{r.l}</span>
                </li>
              ))}
              <li className="flex items-center gap-2">
                <span className="inline-block h-3 w-3 rounded-full border border-dashed border-signal-cyan" aria-hidden="true" />
                <span className="text-lunar-200">selected for comparison</span>
              </li>
            </ul>
            <p className="mt-2 text-lunar-400">
              Keyboard: <span className="kbd">Tab</span> to markers, <span className="kbd">Enter</span> to open; focus map then <span className="kbd">←↑→↓</span> pan, <span className="kbd">+</span>/<span className="kbd">−</span> zoom.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
