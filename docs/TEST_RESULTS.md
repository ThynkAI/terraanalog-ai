# Test results

Recorded 2026-11-15 12:24 EST (America/Toronto) on the dev box. These counts come from actual runs. Raw outputs are in `docs/test-results/`.

## Local (API :8710 via uvicorn, UI :3710 via `PORT=3710 npm start`)
| Suite | Command | Result |
|---|---|---|
| Backend unit/API (pytest), incl. 4 PDF-report tests | `cd backend && python -m pytest -q` | **68 passed**, 0 failed |
| TypeScript | `cd web && npx tsc --noEmit` | **0 errors** |
| Frontend unit (Vitest), incl. 3 deck.gl cluster-arc tests | `cd web && npx vitest run` | **14 passed** (2 files) |
| Production build | `cd web && npx next build` | **success**, 11/11 static pages |
| End-to-end (Playwright, desktop Chromium + Pixel 7), incl. axe serious/critical a11y, PDF download, deck.gl map | `BASE_URL=http://127.0.0.1:3710 npx playwright test` | **40 passed**, 0 failed, 0 flaky |
| Screenshots | `node web/scripts/screenshots.mjs` (`ONLY=06,09,15` for changed views) | 15 app screenshots + 1 PDF page render in `docs/screenshots/` |

## Docker Compose (Docker Compose v5.7.1, Docker Engine 29.1.4)
| Step | Result |
|---|---|
| `API_PORT=18000 WEB_PORT=13000 docker compose -p terraanalog up --build -d` | both images built; api **healthy**, web started |
| Smoke: `/api/health`, all 8 pages, `/api/export/compare.pdf` (via web proxy), `POST /api/recommend` | all HTTP 200; PDF valid (3 pages) |
| Playwright against compose (`BASE_URL=http://127.0.0.1:13000`) | **40 passed**, 0 failed (`playwright-docker-compose.txt`) |

## One-command setup scripts (run in a clean copy of the repo)
| Script | Result |
|---|---|
| `scripts/setup.sh` (bash, Linux) | fresh venv + `npm ci` + build, then API and UI started; health, `/compare` and the PDF endpoint returned 200. The port-in-use check was also exercised (it exits with a clear message). |
| `scripts/setup.ps1` under PowerShell 7.7.0 on **Linux** | parsed with 0 errors, installed, built and started API and UI; health and `/compare` returned 200 |
| `scripts/setup.ps1` on **Windows PowerShell 5.1** | **not executed** (no Windows machine available). The script avoids PS 7-only syntax (`&&`, ternary, `??`) and uses `npm.cmd`, `.venv\Scripts\python.exe` and `py -3` on Windows |

## Not executed
- No cloud deployment (no credentials). The repo contains no deployment URL.
- All scores come from SYNTHETIC fixtures, or are PROVISIONAL from the team prep pack. They are not measurements.
