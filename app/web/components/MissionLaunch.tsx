"use client";
import Link from "next/link";
import { useMeta } from "./MetaContext";

const MISSIONS = [
  { id: "MOON_ISRU_ICE", number: "01", title: "Prospect for lunar ice", body: "Moon", detail: "Compare polar terrain and ice proxies for resource-testing campaigns.", icon: "◈" },
  { id: "MARS_ROVER_MOBILITY", number: "02", title: "Put a Mars rover to work", body: "Mars", detail: "Find terrain and surface-process matches for mobility trials.", icon: "↗" },
  { id: "MOON_LAVA_TUBE", number: "03", title: "Explore below the surface", body: "Moon", detail: "Investigate cave environments for subsurface robotics tests.", icon: "⌒" },
  { id: "MARS_ASTROBIO_SEDIMENTS", number: "04", title: "Follow the evidence of water", body: "Mars", detail: "Compare sedimentary environments for astrobiology fieldwork.", icon: "≋" },
];

export function MissionLaunch() {
  const { meta } = useMeta();
  const available = MISSIONS.filter((m) => meta?.objectives.some((o) => o.id === m.id));
  if (!available.length) return null;
  return (
    <section aria-labelledby="mission-launch-title">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div><p className="panel-title text-signal-cyan">Choose a starting point</p><h2 id="mission-launch-title" className="mt-2 text-2xl font-semibold tracking-tight text-white">What will your mission test?</h2></div>
        <Link href="/methodology" className="link text-xs">Understand the scoring ↗</Link>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {available.map((m) => {
          const objective = meta!.objectives.find((o) => o.id === m.id)!;
          const ref = objective.published_references?.[0] || meta!.default_reference[m.body === "Moon" ? "moon" : "mars"];
          return (
            <Link key={m.id} href={`/explorer?ref=${ref}&obj=${m.id}&body=${m.body.toLowerCase()}`} className="mission-card group">
              <div className="flex items-center justify-between"><span className="font-mono text-xs text-lunar-400">{m.number} / {m.body.toUpperCase()}</span><span aria-hidden="true" className="text-2xl text-mars-300">{m.icon}</span></div>
              <h3 className="mt-6 text-base font-medium text-white group-hover:text-mars-300">{m.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-lunar-300">{m.detail}</p>
              <span className="mt-5 inline-block text-xs font-medium text-signal-cyan">Find Earth analogs <span aria-hidden="true">→</span></span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
