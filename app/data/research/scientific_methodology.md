# TerraAnalog AI: scientific methodology

Version 1.0.0, built 2026-11-15. Scope: rank terrestrial field sites as **analogs for specific mission-testing objectives** at lunar and Martian reference environments, and keep the evidence behind every number traceable.

> **What the scores are not.** A TerraAnalog score is a relative, objective-specific ranking aid. It is **not** a measure of lunar or Martian equivalence. No Earth site reproduces lunar or Martian gravity (the Moon's is about one-sixth of Earth's and about half of Mars's, per wiki:Moon), the lunar vacuum or the thin Martian CO₂ atmosphere, the surface radiation environment, the day length or the temperature regime (lunar PSRs < 100 K). The engine also keeps **surface/process analog fidelity** separate from **operational test suitability** and never merges them.

## 1. Reference environments (Phase 1)

There are 14 references (`config/planetary_references.json` → `outputs/planetary_features.csv`, `outputs/planetary_reference_sites.geojson`):

| ID | Environment | Status class |
|---|---|---|
| MOON-REF-01 | South polar highlands (pole-centred; contains Artemis III candidate regions) | candidate_region |
| MOON-REF-02 | Shackleton crater + rim | representative_region |
| MOON-REF-03 | Malapert massif | candidate_region (Artemis III list, 2024-10-28) |
| MOON-REF-04 | Cabeus PSR (LCROSS impact target) | verified_mission_site (impact, not landing) |
| MOON-REF-05 | Marius Hills pit | representative_region |
| MOON-REF-06 | Mare Tranquillitatis pit | representative_region |
| MOON-REF-07 | Apollo 11 Tranquility Base (mare plains) | verified_mission_site |
| MARS-REF-01 | Jezero delta (Perseverance) | verified_mission_site |
| MARS-REF-02 | Gale crater (Curiosity, Bradbury Landing) | verified_mission_site |
| MARS-REF-03 | Elysium Planitia (InSight) | verified_mission_site |
| MARS-REF-04 | Vastitas Borealis (Phoenix) | verified_mission_site |
| MARS-REF-05 | Planum Boreum north polar layered deposits | representative_region |
| MARS-REF-06 | Arsia Mons flank skylights | representative_region |
| MARS-REF-07 | Arcadia Planitia mid-latitude ground ice | representative_region |

**Coordinates.** All are planetocentric latitude with east-positive longitude, converted to [-180, 180]. The Moon uses IAU_2015:30100 (sphere R = 1737.4 km, as in the LOLA products). Mars uses IAU_2015:49900 (sphere R = 3396.19 km in the MOLA mosaic). These are **not** WGS84.

**Terrain, measured this build.** Each reference's DEM window is reprojected onto a body-fixed azimuthal-equidistant grid centred on the reference:
* Moon polar references: LOLA LDEM_80S_80M from PDS (DN × 0.5 m).
* Moon equatorial references: LOLA global 118 m.
* Mars references: MOLA 463 m.

Slope uses Horn (1981) and ruggedness uses Riley TRI. The window radius is 5 km for most Moon references, 12 km for Shackleton (to include the walls) and 15 km for Mars. Sanity checks pass: Malapert 4,838 m, Gale landing −4,501 m, Arsia caldera floor 16,265 m, InSight plains median slope 0.28°.

**Literature values.** Temperature, illumination, ice evidence and hazards all carry verbatim quotes and their sources in `site_evidence.json`. Mars references use the global mean surface temperature (210 K, low confidence, flagged). The Apollo 11 and Planum Boreum temperatures are **null**, because only a range or a minimum was sourced.

## 2. Earth candidates (Phase 3)

There are 28 sites (`config/earth_sites_master.json`):
* 3 user-specified baselines: Atacama, Haughton, Death Valley.
* 10 established analogs with documented analog use: Dry Valleys, Svalbard/Bockfjorden, Askja, Tso Kar, Qaidam, Craters of the Moon, Meteor Crater, Mistastin, Río Tinto, MDRS.
* 15 further candidates.

Coordinates come from Wikipedia GeoData or infobox coordinate templates (retrieved 2026-11-15, revision IDs recorded). They are **sampling points**, and the `coord_kind` field says what each one represents (for example "region centroid" or "crater centre (lake)"). Boundaries are given as approximate bounding boxes and are labelled as such. No mapped boundary polygons were available in this build.

## 3. Features and provenance (Phase 2 and 4)

| Feature | Earth source (provenance) | Reference source | Similarity function |
|---|---|---|---|
| lithology | curated tags, keyword-verified in cited text (literature / hypothesized) | curated tags (literature / hypothesized) | Jaccard on canonical classes |
| process (volcanic, impact, aqueous, periglacial…) | same | same | Jaccard |
| landform / geomorphology | same | same | Jaccard |
| resource geology | same | same | Jaccard |
| slope | Copernicus DEM GLO-30, block-averaged to the matched baseline (derived) | LOLA / MOLA (derived) | 0.5·G(Δmedian; σ=4°) + 0.5·G(Δp90; σ=6°) |
| ruggedness | TRI at the matched baseline (derived) | TRI (derived) | exp(−\|ln(TRI_e/TRI_r)\|) |
| thermal | CHELSA V2.1 bio1 MAAT, ERA5 fallback (modeled) → K | literature/modeled mean T (K) | G(ΔT; σ=30 K) |
| aridity | ERA5 1991–2020 P/ET0 and P (modeled) | AI = 0, P = 0 (derived) | 0.5·s_AI + 0.5·s_P (see below) |
| ice / permafrost | Obu et al. 2019 probability (modeled), MAAT-logistic model where Obu is unavailable, max with WorldCover snow/ice | 1 if ice evidence, else 0 | 1 − \|I_e − I_r\| |
| abiotic surface | ESA WorldCover 2021 bare/sparse + snow/ice fraction within 5 km, water excluded (derived) | 1 | value itself |
| dust / sediment | SoilGrids 2.0 silt+clay, 0–5 cm (modeled) | Moon 0.45 (derived from "50% < 60–80 µm"); Mars null | G(Δ; σ=0.15) |

G(Δ;σ) = exp(−½(Δ/σ)²). Every similarity lies in [0, 1].

**Provenance classes** (per value): `measured` (direct instrument value), `derived` (computed by us from measured data, e.g. slope from a DEM), `modeled` (reanalysis or model output such as ERA5, CHELSA, SoilGrids or Obu), `literature` (quoted from a fetched source), `hypothesized` (expert assignment without a matching sentence in fetched text), and `unavailable` (null). Default confidences are 0.95 / 0.85 / 0.70 / 0.75 / 0.30 / 0 (`scoring_config.json`).

**Categorical evidence check.** Each tag is written `tag:keyword`. `04_build_features.py` searches the cited fetched text for the keyword and stores the matching sentence and its URL. If the keyword is missing or explicitly marked `?`, the tag is downgraded to `hypothesized`. In this build, 205 of 231 Earth tags are literature-supported.

**Matched baselines.** Slope and roughness are scale-dependent. Lunar references (80–118 m DEMs) are compared with Earth metrics on a 90 m grid within 5 km. Martian references (463 m) are compared with Earth on a 450 m grid within 15 km. Local 30 m / 2 km metrics feed only operational trafficability. Open water (WorldCover class 80) is masked because Copernicus DEM is flattened over water.

**Why the aridity term has two parts.** The P/ET0 index alone would rate cold polar deserts as "humid", because their ET0 is tiny (Haughton has AI 0.73 at 161 mm/yr). The absolute-precipitation term (s_P = 1 at ≤ 50 mm/yr, decaying with a 200 mm scale) corrects for this. The UNEP hyper-arid threshold of AI ≤ 0.05 sets s_AI = 1.

**Permafrost model.** Obu et al. (2019) covers only the Northern Hemisphere above 25°N. Elsewhere, p = 1/(1+exp((MAAT+2)/1)) is used. This is a coarse proxy, labelled `modeled` with confidence reduced to 0.6×.

**Thermal limitation.** For lava-tube references the reference value is the modeled ~290 K inside shadowed pit/cave space (Horvath et al. 2022). The Earth value is the site's mean annual air temperature, used as a proxy for cave interior temperature (a common first-order approximation). In-cave measurements are a recommended field gap.

## 4. Scoring engine (Phase 4)

For site *s*, reference *r* and mission profile *p* with weights *w_i* (Σw_i = 1):

AnalogScore(s,r,p) = 100 × Σ_{i∈A} w_i·sim_i / Σ_{i∈A} w_i

Here *A* is the set of features available for that pair.
* **Evidence completeness** = Σ_{i∈A} w_i, the share of profile weight that had data.
* **Confidence** = the weight-averaged minimum of the Earth and reference provenance confidence per feature.

The profile score is the **best-matching reference** in that profile, and the matched reference is reported. Per-reference scores are in `data/processed/pair_scores.csv`.

There are 10 mission profiles: Moon ISRU-ice, rover mobility, EVA/habitat, field geology and lava tube; Mars ISRU-ice, rover mobility, EVA/habitat, astrobiology/sediments and lava tube. Astrobiology is **not applicable** to the Moon and is replaced there by astronaut field-geology training. The weights were set from mission relevance, are documented in `scoring_config.json` and are tested for sensitivity. They are expert judgements, not fitted parameters.

**Operational test suitability** is computed separately (0–100) and never mixed with fidelity:
* access: exp(−d/25 km) to the nearest mapped road, Natural Earth 1:10m (upper bound)
* trafficability: fraction of 30 m slopes < 15°
* climate workability: fraction of months with ERA5 mean in [−25, 35] °C
* regulatory class
* existing analog infrastructure

## 5. Sensitivity and uncertainty

* **Monte Carlo:** 2,000 Dirichlet weight draws per profile (α = 50·w). Outputs are 5–95% score and rank intervals, top-5 probability and mean Spearman ρ against the base ranking.
* **One-at-a-time:** each weight ×(1 ± 0.2), renormalised, recording the maximum rank shift.
* **Leave-one-feature-out:** Spearman ρ and changes in the top 5.
* **Evidence-strict variant:** all `hypothesized` tags removed, then the profiles are re-ranked.

## 6. Analytics (Phase 5): unsupervised only

There is no labelled "true analog" dataset, so **no supervised model is trained and no predictive accuracy is claimed**.
* PCA and k-means (k chosen by silhouette, 2–6) run on 10 standardised numeric features. They are cross-checked with Ward clustering using the adjusted Rand index.
* Similarity matrices: site × reference (equal-weight mean similarity) and site × site (cosine on standardised features).
* Radar-chart data covers the top 5 sites per profile.
* Baseline comparison: mean rank percentiles for baseline, established and candidate sites, plus expected-role checks against literature analog uses.
* With n = 28, clusters are exploratory descriptions only.

## 7. Known limitations

1. Sampling points can be region centroids (Atacama, Qaidam) and may miss the best outcrops.
2. CHELSA and ERA5 are modeled. ERA5 at 0.25° can sit at a different elevation from the site (the grid elevation is recorded).
3. SoilGrids is masked or unreliable on bare rock and ice (Dry Valleys, Askja and others are null).
4. WorldClim 2.1 and OSM Overpass were **blocked** from the build host by TLS refusal. CHELSA and Natural Earth roads were substituted, and the retrieval code is provided.
5. MODIS LST, ERA5 via CDS, Landsat and Sentinel-2 need credentials and were **not** used. Their observations are unavailable.
6. Orbital spectral mineralogy (CRISM, OMEGA) and high-resolution imagery (HiRISE, CTX, LROC NAC) were not quantitatively ingested. Reference mineralogy comes from literature tags.
7. Categorical tags draw on Wikipedia, a tertiary source, so peer-reviewed primary sources should replace them before scientific publication. Verified DOIs are listed in `source_references.md`.
8. Similarity widths (σ) are documented choices. The sensitivity analysis covers the weights but not the σ values. A σ sweep is recommended future work.


## App data-contract export (scripts/13_export_app_contract.py, source commit 195b7a8)

**Criteria.** The app's score is `100 * sum(w_c * x_c/5) / sum_present(w_c)` with one value per (site, criterion). TerraAnalog fidelity is a similarity to a specific reference, so the export uses **reference-specific criteria** `<REF_ID>.<feature>` (11 features x 14 references = 154) with `x = 5 x similarity`. `body_weights` = 1 for criteria of that body's references, `reference_multipliers[ref]` = 0 for the other references of the same body, and each objective's multipliers are the TerraAnalog mission-profile feature weights (`general` = equal weights; it is not a TerraAnalog profile). With this setup the app's live score for (reference, profile) equals the published fidelity in `analog_rankings.csv`. `min_completeness` = 0.5 (the lowest TerraAnalog pair completeness is 0.70, so no published score is suppressed).
**Operational separation.** `operational_suitability` (= operational score / 20) has weight 0 everywhere. It is displayed and is never part of fidelity.

**value_type mapping** (TerraAnalog provenance -> app):

| TerraAnalog class / input | app value_type | default confidence |
|---|---|---|
| derived from instrument DEMs (slope, TRI: Copernicus DEM vs LOLA/MOLA) | measured | 0.85 |
| modeled (CHELSA, ERA5, SoilGrids, Obu et al. permafrost) | modeled | 0.70 (min with reference-side confidence) |
| derived from a classified product (WorldCover unvegetated fraction) | modeled | 0.70 |
| in-house simple model (MAAT-logistic permafrost fallback) | provisional | 0.50 |
| literature-text categorical tags (Wikipedia sentences found) | provisional | 0.75 per tag, averaged with hypothesized tags |
| hypothesized tags (no supporting sentence) | provisional | 0.30 per tag |
| unavailable | missing (empty value, never imputed) | - |

Thermal values are always `modeled`, even where the reference temperature is a published measurement (Diviner), because the Earth side is a modeled air-temperature normal. Literature numbers are not exported as `measured` unless the underlying instrument data were read by this package.

**Analog types** (`analog_types`) are derived from tags and data using fixed rules in the export script:
* lava tube/pit landform -> lava_tube_cave
* impact process or crater -> impact_crater
* ground-ice tag, periglacial process or permafrost probability >= 0.5 -> permafrost_ice
* MAAT <= -10 deg C and P <= 250 mm/yr -> polar_desert
* basalt or effusive volcanism -> basaltic_volcanic
* references: literature ice evidence -> permafrost_ice, plus polar_desert if |lat| >= 60; every Mars reference -> arid_desert; Arsia Mons -> high_altitude
* hydrothermal/acidic process, clay or sulfate -> aqueous_alteration
* evaporitic process or salt flat -> evaporite_basin
* P/ET0 < 0.2 (and not polar) -> arid_desert
* elevation >= 3000 m -> high_altitude

`mission_objectives` lists the TerraAnalog profiles where the site ranks in the top quartile (rank <= 7 of 28).

**Known contract mismatches.**
1. 155 criteria instead of a handful. This keeps the app's live score identical to the TerraAnalog fidelity, at the cost of long criterion lists in the UI. The app may group criteria by the extra `ref_id` and `feature` keys on each criterion.
2. `region` is empty, because no region field was sourced.
3. `imagery` is null, because no licensed imagery was gathered.
4. `gazetteer_feature_id` is null, because the USGS Gazetteer was not queried by this package.
5. `diameter_km` is null except where a fetched source states it.
6. `target_bodies` lists both bodies for every site, because every site is scored against both.
