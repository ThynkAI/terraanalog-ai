# Challenge review and experience improvements

Review date: 15 November 2026. Repository reviewed at `f47f95c`.

The project addresses Earth analog identification with a curated 28-site catalog, 14 Moon/Mars references, explainable weighted scoring, maps, evidence inspection, sensitivity analysis, comparison and exports. This update makes mission selection and candidate investigation more discoverable and improves request recovery. It does not add new scientific measurements.

## Changes

- Mission overview with a real catalog globe, responsive layout and four mission shortcuts. Shortcuts take reference IDs from the loaded objective configuration, rather than assuming the general default reference is appropriate.
- Candidate discovery entry point and shareable `group` explorer filter, backed by `catalog_group` on `/api/sites`. Labels come from the existing research export's `group` field: baseline, established, candidate. Scores and full-catalog ranks are preserved under filtering. Candidate status means a curated research lead; it does not assert that a site has never been studied before.
- More prominent interpretation guidance: fidelity is objective-specific, evidence completeness matters, operational suitability stays separate, and planetary environmental conditions cannot be reproduced wholesale on Earth.
- GET retries for transient 502/503/504 and network failures (three total attempts, abortable backoff); manual recovery controls for metadata, rankings and site evidence. Invalid queries are not retried. POSTs are never automatically retried.
- Results tied to the active request, cancellation of superseded recommendation requests, unique recommendation form labels, and geographic search synchronized with URL navigation.
- Mobile explorer places the map and evidence before the long results list; smaller screens get larger button targets. Existing keyboard and reduced-motion behavior is retained.
- GitHub Actions workflow for backend regression tests, frontend unit tests, production build, desktop/mobile flows and accessibility checks.

## Verification performed for this change (historical counts from revision `f47f95c`)

| Check | Result |
|---|---|
| Backend `pytest backend/tests -q` | 90 passed; one upstream Starlette deprecation warning |
| Frontend `npm test` | 19 passed across three files |
| `npm run build` | Passed, including TypeScript and all 11 generated pages |
| `git diff --check` | Passed |
| Catalog filter regression tests | Preserve scores and ranks, compose with geography, reject unsupported groups |
| Recovery regression tests | Transient recovery, bounded retries, cancellation, no retry on 422 or POST |
| Browser / visual / accessibility checks for this revision | Not executed locally: the managed preview runner appends Vite-style `--host` / `--strictPort` arguments, which Next.js rejects. New mission/candidate flows are included in the browser suite for CI; CI status must be checked separately. Prior screenshots and browser results describe the earlier revision. |

These checks are software/data-contract checks. They do not constitute field validation or independent remeasurement of the underlying datasets.

## Scientific strengths and remaining limits

The reference-side distinction between candidate regions, representative regions and visited mission sites is appropriate. NASA's [October 2024 Artemis landing-region update](https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/) describes candidate regions for further scientific and engineering study. It does not establish permanent-base approvals. [NASA's Planetary Analog Explorer](https://science.nasa.gov/solar-system/analog-explorer/) illustrates the process-specific nature of Earth analog comparisons, including caves and terrain features.

The challenge's strongest remaining research opportunity is demonstrating why a candidate adds something beyond well-studied analogs. A curated label or a high proxy score alone cannot establish novelty. Before claiming a new validated analog, conduct a targeted literature search for that site and mission use, document the spatial scale/resolution and temporal support of the comparison, identify missing measurements, and obtain appropriate field evidence. Site access and permissions also require confirmation for any expedition.

The current catalog is finite rather than a global automated search. Some inputs remain modeled or provisional; incomplete evidence can make a seemingly strong score less informative. The existing completeness, provenance, data-gap and sensitivity views should accompany any shortlist. The underlying 588-score reproduction regression remains in the backend test suite.

## Submission and deployment

Repository URL for the form: https://github.com/ThynkAI/terraanalog-ai

No submission-form URL was supplied, so no form was completed. This change is prepared as a pull request. The existing Render app must deploy the merged revision before the new interface is live. Do not use the old screenshots as evidence of this revision, or describe the new browser checks as passing until CI has actually executed them. Record a fresh demo after deployment.
