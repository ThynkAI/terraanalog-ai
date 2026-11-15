> **SYNTHETIC FIXTURE — NOT REAL DATA. Replace with Bot 1 research outputs (see docs/DATA_INTEGRATION.md).**
> This methodology describes the TerraAnalog scoring engine as implemented. Bot 1's `scientific_methodology.md` will replace this file.

# Scientific methodology (fixture edition)

## 1. Question being answered
For a chosen **planetary reference region** (Moon or Mars) and a chosen **mission objective**, which Earth field sites are the most useful
*operational and environmental proxies* for testing hardware, procedures and crews?

Analog scores are **not** landing-site selections, do not certify flight hardware, and never claim that Earth reproduces the planetary environment.

## 2. Criteria (0–5 scale)
| Criterion | Earth proxy (planned source) |
|---|---|
| Terrain similarity | Copernicus DEM / SRTM slope & roughness |
| Geological similarity | USGS planetary analog resources + literature |
| Thermal / environmental similarity | MODIS / VIIRS land-surface temperature |
| Dust & aridity | Precipitation climatology, aridity index, SMAP |
| Illumination contrast | Latitude + DEM hillshade / insolation |
| Ice / permafrost relevance | Permafrost maps, field reports |
| Subsurface / cave access | Cave surveys |
| Operational testing suitability | OpenStreetMap + published field logistics |

## 3. Weighting
`w_c = body_weight[body][c] × reference_multiplier[ref][c] × objective_multiplier[objective][c] × user_multiplier[c]`

Body weights for six criteria follow the team's AnalogSite v0 method (Moon emphasises illumination contrast; Mars emphasises dust/aridity and thermal).
Reference and objective multipliers are listed in `scoring_config.json` and shown in the UI.

## 4. Score, completeness and confidence
* **Score** (0–100) = `100 × Σ w_c·x̂_c / Σ_present w_c`, with `x̂ = (x − min)/(max − min)`.
* **Evidence completeness** = `Σ_present w_c / Σ_all w_c`.
* **Missing values are never imputed.** If completeness < **0.70** the site is shown as *insufficient evidence* with no point score.
* Every score carries a **plausible range**: missing criteria set to the scale minimum (low) and maximum (high).
* **Confidence** = completeness × weighted mean of per-value confidence (measured 0.9, modeled 0.7, provisional 0.5, synthetic 0.25 unless a value states its own).

## 5. Sensitivity
Each criterion's weight is swept from 0× to 2× and the resulting scores and ranks are reported; rank shifts under ±50 % perturbation indicate robustness.

## 6. Clustering
Mask-aware k-means on criterion vectors (distance over shared, present criteria only) groups candidate environments without imputation.

## 7. What Earth cannot replicate
Gravity (1/6 g Moon, ~0.38 g Mars), vacuum / thin CO₂ atmosphere, space radiation, cryogenic PSR temperatures, lunar regolith electrostatics,
Martian global dust storms and planetary-protection conditions. These are listed with every recommendation.

## 8. Planetary coordinates
Reference coordinates come from the IAU/USGS Gazetteer of Planetary Nomenclature (planetocentric/IAU body-fixed, east-positive longitude).
They are displayed in body-specific viewers (equirectangular and south-polar stereographic on a sphere of the body's IAU mean radius). No Earth
geodetic (WGS84) assumptions are applied to Moon or Mars geometry.
