export const VALUE_TYPE_STYLE: Record<string, { label: string; cls: string; desc: string }> = {
  measured: { label: "Measured", cls: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/40", desc: "Derived from instrument / observational data (e.g. DEMs)" },
  modeled: { label: "Modeled", cls: "bg-sky-500/15 text-sky-300 ring-sky-400/40", desc: "Output of a model or interpolation" },
  provisional: { label: "Provisional", cls: "bg-amber-500/15 text-amber-300 ring-amber-400/40", desc: "Literature-derived tags, expert classes or simple models — not an instrument measurement" },
  synthetic: { label: "Synthetic", cls: "bg-pink-500/15 text-pink-300 ring-pink-400/40", desc: "Generated placeholder — not real data" },
  missing: { label: "Missing", cls: "bg-slate-500/10 text-slate-400 ring-slate-500/40 border-dashed", desc: "No value; never imputed" },
};

export const ANALOG_TYPE_COLORS: Record<string, string> = {
  polar_desert: "#9ed6f0",
  permafrost_ice: "#67d4ee",
  basaltic_volcanic: "#f08a55",
  impact_crater: "#c9ced6",
  lava_tube_cave: "#a78bfa",
  hyperarid_desert: "#fbbf24",
  acidic_aqueous: "#34d399",
  high_altitude: "#f472b6",
  // research-dataset types
  aqueous_alteration: "#34d399",
  evaporite_basin: "#e5e7eb",
  arid_desert: "#fbbf24",
};

export const BODY_COLORS = { moon: "#c9ced6", mars: "#e8743b" } as const;

export const NAV = [
  { href: "/", label: "Mission Overview" },
  { href: "/explorer", label: "Earth Analog Explorer" },
  { href: "/moon", label: "Moon Reference" },
  { href: "/mars", label: "Mars Reference" },
  { href: "/compare", label: "Comparison Lab" },
  { href: "/methodology", label: "Methodology" },
  { href: "/data", label: "Data & Provenance" },
  { href: "/impact", label: "Impact & Team" },
];

export const EXAMPLE_QUERIES = [
  "Find Earth environments suitable for testing lunar polar rovers.",
  "Identify basaltic terrain analogous to Martian volcanic plains.",
  "Compare Earth sites for Mars drilling equipment testing.",
  "Find polar desert environments relevant to lunar resource prospecting.",
  "Identify cave environments suitable for subsurface robotics tests.",
];
