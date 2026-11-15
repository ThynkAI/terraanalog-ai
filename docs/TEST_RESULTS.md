# Test results

Recorded 2026-11-15 13:20 EST (America/Toronto) on the dev box, with the **research dataset** (`data/research/`, the default
`TERRA_DATA_DIR`). These counts come from actual runs. Raw outputs are in `docs/test-results/`.

## Local (API :8710 via uvicorn on data/research, UI :3710 via `PORT=3710 npm start`)
| Suite | Command | Result |
|---|---|---|
| Backend unit/API (pytest) | `.venv/bin/python -m pytest -q backend` | **84 passed**, 0 failed (68 on the synthetic fixtures, incl. 4 PDF tests, for backward compatibility + 16 on the research data) |
| TypeScript | `cd web && npx tsc --noEmit` | **0 errors** |
| Frontend unit (Vitest), incl. 3 deck.gl cluster-arc tests | `cd web && npx vitest run` | **14 passed** (2 files) |
| Production build | `cd web && npx next build` | **success**, 11/11 static pages |
| End-to-end (Playwright, desktop Chromium + Pixel 7), incl. axe serious/critical a11y, PDF download, deck.gl map, research-data badge, value-type badges, default-reference note | `BASE_URL=http://127.0.0.1:3710 npx playwright test` | **41 passed**, 0 failed, 0 flaky |
| Data validation | `python scripts/validate_data.py data/research` | exit 0 (no errors) |
| Published-score reproduction | `python scripts/verify_published.py data/research --json docs/test-results/published_reproduction.json` | see below; exit 0 |
| Screenshots | `BASE_URL=… node web/scripts/screenshots.mjs` | 16 app screenshots + 1 PDF page render in `docs/screenshots/`, all from research data |

The 16 research-data tests (`backend/tests/test_research_data.py`) cover: synthetic flag false and *Research dataset* label; counts
(28 sites, 14 references, 155 criteria, 4,340 values, 460 missing, no synthetic value types); missing values never imputed; per-reference
active criteria (12 per reference, other references excluded); feature grouping with readable labels; compare/CSV/PDF limited to the
selected reference; default-reference note; objective/body mismatch note; feature-keyed sensitivity and clusters; status_class on
references; the recommendation engine choosing a published reference; and reproduction of all 588 published scores.

Backward compatibility: the synthetic fallback (`TERRA_DATA_DIR=data/fixtures`) still passes the 68 original backend tests, and a
headless smoke run of all pages on fixtures (API :8711, UI :3711) showed the *Synthetic fixture data* badge and no page errors.

## Published-score reproduction (all 588 rows, 21 reference × objective pairs)
| Metric | Value |
|---|---|
| Rows compared / unscorable | 588 / 0 |
| abs(engine score − published score), unrounded | max **0.0111**, mean **0.0031**, median 0.0030; 588/588 within 0.05, 587/588 within 0.01 |
| abs diff of the 1-dp display value | max 0.05, mean 0.0256 |
| Completeness difference | 0 (all rows identical) |
| Rank agreement | 584/588; the 4 differing rows are 2 swaps where the published scores tie at 2 dp (MARS-REF-01/MARS_ASTROBIO_SEDIMENTS EA-006 vs EA-027 at 26.84; MOON-REF-02/MOON_ISRU_ICE EA-018 vs EA-028 at 14.18) |
Residuals come from the exported values being rounded to 3 dp after the published scores were computed. Full report:
`docs/test-results/published_reproduction.json`.

## Docker Compose (Docker Compose v5.7.1, Docker Engine 29.1.4)
| Step | Result |
|---|---|
| `API_PORT=18000 WEB_PORT=13000 docker compose -p terraanalog up --build -d` | both images built; api **healthy** with `data/research` (`synthetic: false, sites: 28, references: 14, errors: 0`) |
| Smoke: `/compare` via web, `/api/export/compare.pdf` via the web proxy | HTTP 200; PDF valid (5 pages) |
| Playwright against compose (`BASE_URL=http://127.0.0.1:13000`) | **41 passed**, 0 failed (`playwright-docker-compose.txt`) |
The stack was stopped afterwards (`docker compose -p terraanalog down`).

## One-command setup scripts
| Script | Result |
|---|---|
| `scripts/setup.sh` | syntax check (`bash -n`) passed after switching the default to `data/research`; the full clean-copy run was done in the previous round (fresh venv + `npm ci` + build + start; health, `/compare`, PDF 200) |
| `scripts/setup.ps1` | parsed with 0 errors under PowerShell 7.7.0 on Linux; full install/start was run in the previous round |
| `scripts/setup.ps1` on **Windows PowerShell 5.1** | **not executed** (no Windows machine available). The script avoids PS 7-only syntax (`&&`, ternary, `??`) |

## Not executed
- No cloud deployment (no credentials). The repo contains no deployment URL.
- Scores are research-package similarity proxies (measured / modeled / provisional values, with missing values shown as missing).
  They are decision support, not landing-site selections.
