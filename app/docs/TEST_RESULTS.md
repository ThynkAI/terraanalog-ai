# Test results

Current reproduction figures and test counts are in **Final submission pass**. The sections from *Local* through *Not re-executed in the 14:20 EST data-update pass* are historical records of the 13:20 and 14:20 EST (America/Toronto) revisions on 15 November 2026, after ingesting the corrected research export (`data/research/`, package `@ d2e464b`, plus `supplementary/`). Those counts come from actual runs at the time. Raw outputs are in `docs/test-results/`.

## Local (historical: 13:20 / 14:20 EST passes; API :8710 via uvicorn on data/research, UI :3710 via `PORT=3710 npm start`)
| Suite | Command | Result |
|---|---|---|
| Backend unit/API (pytest) | `.venv/bin/python -m pytest -q backend` | **85 passed**, 0 failed (68 on the synthetic fixtures, incl. 4 PDF tests, for backward compatibility + 17 on the research data) |
| TypeScript | `cd web && npx tsc --noEmit` | **0 errors** |
| Frontend unit (Vitest), incl. 3 deck.gl cluster-arc tests | `cd web && npx vitest run` | **14 passed** (2 files) |
| Production build | `cd web && npx next build` | **success**, 11/11 static pages |
| End-to-end (Playwright, desktop Chromium + Pixel 7), incl. axe serious/critical a11y, PDF download, deck.gl map, research-data badge, value-type badges, default-reference note | `BASE_URL=http://127.0.0.1:3710 npx playwright test` | **41 passed**, 0 failed, 0 flaky |
| Data validation | `python scripts/validate_data.py data/research` | exit 0 (no errors) |
| Published-score reproduction | `python scripts/verify_published.py data/research --json docs/test-results/published_reproduction.json` | see below; exit 0 |
| Screenshots | `BASE_URL=… node web/scripts/screenshots.mjs` | 16 app screenshots + 1 PDF page render in `docs/screenshots/`, all from research data |

The 17 research-data tests (`backend/tests/test_research_data.py`) cover: synthetic flag false and *Research dataset* label; counts
(28 sites, 14 references, 155 criteria, 4,340 values, 378 missing, no synthetic value types); missing values never imputed; per-reference
active criteria (12 per reference, other references excluded); feature grouping with readable labels; compare/CSV/PDF limited to the
selected reference; default-reference note; objective/body mismatch note; feature-keyed sensitivity and clusters; status_class on
references; the recommendation engine choosing a published reference; reproduction of all 588 published scores; and the corrected-export fields (Köppen/aridity classes, region, imagery attribution, Gazetteer, operational confidence, explained missing-evidence statements, and supplementary profile rankings / published sensitivity / radar).

Backward compatibility: the synthetic fallback (`TERRA_DATA_DIR=data/fixtures`) still passes the 68 original backend tests, and a
headless smoke run of all pages on fixtures (API :8711, UI :3711) showed the *Synthetic fixture data* badge and no page errors.

## Published-score reproduction (historical four-decimal summary; precise residual in Final submission pass)
| Metric | Value |
|---|---|
| Rows compared / unscorable | 588 / 0 |
| abs(engine score − published score), unrounded | max **0.00004737**, mean **0.0**, median 0.0; 588/588 within 0.01 (older four-decimal summaries displayed the max as 0.0) |
| abs diff of the 1-dp display value | max 0.05, mean 0.0258, 4 exact |
| Completeness difference | 0 (all rows identical) |
| Rank agreement | **588/588** (0 mismatches) |
Full report: `docs/test-results/published_reproduction.json`.

## Docker Compose (historical; Docker Compose v5.7.1, Docker Engine 29.1.4)
| Step | Result |
|---|---|
| `API_PORT=18000 WEB_PORT=13000 docker compose -p terraanalog up --build -d` | both images built; api **healthy** with `data/research` (`synthetic: false, sites: 28, references: 14, errors: 0`) |
| Smoke: `/compare` via web, `/api/export/compare.pdf` via the web proxy | HTTP 200; PDF valid (5 pages) |
| Playwright against compose (`BASE_URL=http://127.0.0.1:13000`) | **41 passed**, 0 failed (`playwright-docker-compose.txt`) |
The stack was stopped afterwards (`docker compose -p terraanalog down`).

## Render free-tier memory check (historical; 2026-11-15 ~14:00 EST, Docker cgroup limits on the dev box)
| Check | Result |
|---|---|
| `next build` with `NODE_OPTIONS=--max-old-space-size=460` (no container memory limit) | **success** (exit 0), 11/11 pages; peak container memory ~1.0 GB |
| `next build` inside a hard **512 MB** container (heap caps of 460 and 300 MB, with and without one build worker and webpack memory optimizations) | **fails**: the build worker is OOM-killed. A 512 MB machine cannot build this app. Render runs builds on its separate build pipeline (Starter tier: 2 CPU / 8 GB), so this does not block the Blueprint |
| Runtime: API (`uvicorn`, data/research) and web (`next start`, `NODE_OPTIONS=--max-old-space-size=460`, `API_HOST=<api>:8000`), each in its own 512 MB container | all 8 pages, `/api/*` proxy, clusters, sensitivity and a 4-site PDF returned 200; desktop Playwright **31 passed** against the capped web container; peak memory **web 105 MB, API 72 MB**, 0 OOM kills |

## One-command setup scripts (historical)
| Script | Result |
|---|---|
| `scripts/setup.sh` | syntax check (`bash -n`) passed after switching the default to `data/research`; the full clean-copy run was done in the previous round (fresh venv + `npm ci` + build + start; health, `/compare`, PDF 200) |
| `scripts/setup.ps1` | parsed with 0 errors under PowerShell 7.7.0 on Linux; full install/start was run in the previous round |
| `scripts/setup.ps1` on **Windows PowerShell 5.1** | **not executed** (no Windows machine available). The script avoids PS 7-only syntax (`&&`, ternary, `??`) |

## Live Render deployment (historical; verified 2026-11-15 ~13:56–13:58 EST, America/Toronto)
Both Blueprint services were Live on commit `7238b1e` before this data update. Measured with curl (services were already warm from
deploy health checks; a true free-tier cold start was not observed and can take ~1 minute after idle sleep).

| Check | Result |
|---|---|
| API `GET /api/health` | HTTP 200 in 0.089 s, then 0.078 s; `{"status":"ok","version":"1.0.0","synthetic":false,"sites":28,"references":14,"errors":0}` |
| API `GET /api/sites` | HTTP 200 in 0.095 s / 0.106 s; 28 sites; first site EA-014 |
| Web `/` (first / second) | HTTP 200, 0.116 s / 0.081 s, 14 465 bytes, title TerraAnalog AI — Earth as a Testbed for Moon and Mars |
| Web `/explorer` `/compare` `/data` `/impact` `/mars` `/moon` `/methodology` | all HTTP 200 in 0.074–0.089 s, correct titles |
| Web proxy `/api/health` and `/api/sites` | HTTP 200, 0.427 s and 0.202 s; same JSON as the API (`synthetic: false`, 28 sites) |
| API and web-proxy `/api/export/compare.pdf?ids=EA-014,EA-001` | HTTP 200, 13 298 bytes, `Content-Type: application/pdf`, magic `%PDF-1.4` |

Live URLs: https://terraanalog-web-cqgu.onrender.com and https://terraanalog-api-cqgu.onrender.com. A later push of this data update retriggers auto-deploy; re-verify after that deploy is Live.

## Not re-executed in the 14:20 EST data-update pass (historical)
- Playwright e2e (previously 41 passed against research data and Docker Compose) and a fresh `next build` / Docker Compose run.
- Scores are research-package similarity proxies (measured / modeled / provisional values, with missing values shown as missing).
  They are decision support, not landing-site selections.

## Final submission pass

The current audit reports are `test-results/submission-sanity.json` and `test-results/submission-score-reproduction.json`. Seventeen committed-data checks pass across 2,352 compatible site scores. All 588 published ranks agree. The maximum unrounded score difference is **0.00004737 points**, which older four-decimal summaries displayed as 0.0. The displayed one-decimal scores can differ from the published four-decimal values by up to 0.05 points due to rounding.

The final pass reran 97 backend tests, 19 frontend unit tests, and the production build locally. GitHub Actions run 43764106365 passed the committed-data audit, 97 backend tests, 19 frontend unit tests, and all 50 desktop/mobile/keyboard/accessibility checks. Final captures wait for the globe to finish initializing. The seven-slide PDF was regenerated and all pages visually inspected. Earlier sections above describe earlier revisions and their historical test counts. A raw-raster retrieval/rederivation and independent field validation were not repeated in this pass.

