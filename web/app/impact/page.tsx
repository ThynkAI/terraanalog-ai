import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Project Impact and Team" };

const ROADMAP = [
  ["Now", "Working platform on synthetic fixtures; real IAU/USGS planetary coordinates; transparent scoring, evidence, sensitivity, clustering, export."],
  ["Next", "Drop in the research bot's datasets (DEM slope/roughness, MODIS LST, permafrost, cave surveys) via TERRA_DATA_DIR; peer-reviewed citations per attribute."],
  ["Then", "Per-pair similarity from planetary rasters (LOLA, Diviner, MOLA, THEMIS) instead of site-level criteria; uncertainty propagation."],
  ["Later", "Field-campaign planner (logistics, season windows), community-contributed analog sites with review workflow, and API access for mission teams."],
];

export default function Page() {
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Why it matters" title="Project Impact and Team">
        Every lunar and Martian system is rehearsed on Earth first. Choosing the right analog site saves field seasons, money and risk — but the
        evidence is scattered across datasets, papers and institutional memory. TerraAnalog AI makes that choice explicit, comparable and auditable.
      </PageHeader>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[
          ["For mission engineers", "Find where to shake down rovers, drills, ISRU plants and habitats against a named lunar or Martian region — with the factors that matter for their objective."],
          ["For scientists", "Every score decomposes into criteria, value types, sources and confidence. Missing evidence lowers completeness instead of being silently guessed."],
          ["For judges & the public", "A three-minute path from a planetary region to ranked Earth sites, with an honest list of what Earth can never reproduce."],
        ].map(([t, d]) => (
          <section key={t} className="panel p-5"><h2 className="text-base font-semibold text-white">{t}</h2><p className="mt-2 text-sm text-lunar-300">{d}</p></section>
        ))}
      </div>
      <section className="panel p-5" aria-labelledby="team-h">
        <h2 id="team-h" className="panel-title">Team</h2>
        <ul className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <li className="rounded-lg border border-white/10 p-3"><p className="font-medium text-white">Deep Kanabar</p><p className="text-xs text-lunar-300">Project lead · NASA Space Apps Challenge 2026</p></li>
          <li className="rounded-lg border border-white/10 p-3"><p className="font-medium text-white">Research bot (Bot 1)</p><p className="text-xs text-lunar-300">Planetary science &amp; geospatial analysis — authoritative data-contract files</p></li>
          <li className="rounded-lg border border-white/10 p-3"><p className="font-medium text-white">Platform bot (Bot 2)</p><p className="text-xs text-lunar-300">Software architecture, visualization, integration, testing &amp; demo</p></li>
        </ul>
      </section>
      <section className="panel p-5" aria-labelledby="road-h">
        <h2 id="road-h" className="panel-title">Roadmap</h2>
        <ol className="mt-3 space-y-3">
          {ROADMAP.map(([k, v]) => (
            <li key={k} className="flex gap-3"><span className="w-14 shrink-0 font-mono text-sm text-mars-300">{k}</span><span className="text-sm text-lunar-200">{v}</span></li>
          ))}
        </ol>
      </section>
      <section className="panel p-5" aria-labelledby="lim-h">
        <h2 id="lim-h" className="panel-title">Honest limitations</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-lunar-300">
          <li>Current scores are synthetic or provisional (PREP_DRAFT) placeholders until the research datasets arrive.</li>
          <li>Analog scores rank operational/environmental proxy value — not landing sites, and not flight qualification.</li>
          <li>No Earth site reproduces reduced gravity, vacuum or a thin CO₂ atmosphere, or space radiation.</li>
        </ul>
        <p className="mt-3 text-sm"><Link className="link" href="/methodology">Read the methodology</Link> · <Link className="link" href="/data">Inspect provenance</Link></p>
      </section>
    </div>
  );
}
