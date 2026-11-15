# Presentation outline (6–8 slides)

1. **Title** — TerraAnalog AI: Earth as a Testbed for Moon and Mars. Team: Deep Kanabar (lead), research bot (planetary science & geospatial), platform bot (software & visualization).
2. **Problem** — Analog site choice drives cost/risk of every field campaign; evidence is scattered; uncertainty rarely explicit; Earth's
   limits (gravity, vacuum/CO₂ atmosphere, radiation, PSR cryogenics) are easy to forget.
3. **Innovation** — Mission-objective-aware ranking against named planetary references; transparent breakdown; completeness/confidence and
   score ranges instead of false precision; evidence inspector; explainable (non-generative) recommendation engine; live weight lab,
   sensitivity, clustering; drop-in data contract.
4. **Scientific method** — 11 reference-specific similarity features (lithology, process, landform, resource, slope, ruggedness, thermal,
   aridity, ice/permafrost, abiotic surface, fine sediment) × 14 references = 154 criteria, plus a separate operational-suitability score;
   weights = body × reference × objective × user; missing never imputed; min completeness 0.50; planetocentric coordinates, IAU radii,
   no WGS84 on Moon/Mars; 4,340 values (770 measured, 1,519 modeled, 1,673 provisional, 378 missing). All 588 published ranks
   agree, with a maximum unrounded difference of 0.00004737 points.
5. **Live demo** — follow `DEMO_SCRIPT.md` (3 min): recommend → Moon/Shackleton → Earth globe → Comparison Lab → export (28 sites, research dataset).
6. **Architecture & quality** — Next.js + MapLibre + Recharts UI; FastAPI scoring service; Docker; tests: pytest, vitest, Playwright + axe +
   mobile (see TEST_RESULTS.md for executed counts).
7. **Impact** — faster, auditable campaign planning for Artemis-era and Mars teams; education/outreach; reusable open data contract.
8. **Roadmap** — ingest research datasets (DEM, LST, permafrost, caves) → per-pair raster similarity (LOLA/Diviner/MOLA/THEMIS) →
   uncertainty propagation → campaign planner & community submissions. Honest limitations slide: scores are proxies, not landing sites.
