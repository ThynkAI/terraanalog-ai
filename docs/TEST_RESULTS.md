# Test results

Recorded 2026-11-15 12:05 EST (America/Toronto) on the dev box. These counts come from actual runs. Raw outputs are in `docs/test-results/`.

| Suite | Command | Result |
|---|---|---|
| Backend unit/API (pytest) | `cd backend && python -m pytest -q` | **64 passed**, 0 failed |
| TypeScript | `cd web && npx tsc --noEmit` | **0 errors** |
| Frontend unit (Vitest) | `cd web && npx vitest run` | **11 passed** (1 file) |
| Production build | `cd web && npx next build` | **success**, 11/11 static pages |
| End-to-end (Playwright, desktop Chromium + Pixel 7) incl. axe serious/critical a11y checks | `BASE_URL=http://127.0.0.1:3710 npx playwright test` | **38 passed**, 0 failed, 0 flaky |
| Screenshots | `node web/scripts/screenshots.mjs` | **14/14** captured into `docs/screenshots/` |
| Route smoke | curl on all 8 pages + /api/health | all HTTP 200 |

## Docker (earlier in the same session)
- `backend/Dockerfile` and `web/Dockerfile` were both built successfully as images `terraanalog-api:dev` and `terraanalog-web:dev`.
- I ran both containers with `docker run` on a user network. `/api/health` and `POST /api/recommend` responded OK through the web proxy, and Playwright passed **38/38** against the containers.
- `docker compose up` was **not executed** because no compose plugin was available. The `docker-compose.yml` mirrors the commands that were verified.

## Not executed
- No cloud deployment (no credentials). The repo contains no deployment URL.
- All scores come from SYNTHETIC fixtures, or are PROVISIONAL from the team prep pack. They are not measurements.
