# Deployment

No hosting credentials were available during the build, so **nothing has been deployed and no public URL exists**. The project is
ready for either option below.

## Option A — single Docker host (simplest; e.g. a VM, Fly.io machine, Render, Railway)
```bash
docker compose up --build -d          # UI :3000, API :8000 (verified 2026-11-15 with Docker Compose v5.7.1 on host ports 18000/13000)
API_PORT=18000 WEB_PORT=13000 docker compose up --build -d   # alternative host ports
```
* `web` image: Next.js standalone server (`node server.js`), env `API_URL=http://api:8000`.
* `api` image: FastAPI + uvicorn, env `TERRA_DATA_DIR` (fixtures by default), healthcheck on `/api/health`.
* Put a TLS reverse proxy (Caddy/nginx/Traefik or the platform's) in front of port 3000. Only the UI needs to be public; the API can stay internal.
* Real data: mount Bot 1's folder at `/app/data/real` and set `TERRA_DATA_DIR=/app/data/real`.

## Option B — Vercel (UI) + Render or Fly.io (API)
1. **API on Render**: New Web Service → Docker → Dockerfile path `backend/Dockerfile`, context repo root, port 8000, health check
   `/api/health`. Env: `TERRA_DATA_DIR=/app/data/fixtures` (or bake/mount real data), `TERRA_CORS_ORIGINS=https://<your-vercel-domain>`.
   (Fly.io: `fly launch --dockerfile backend/Dockerfile`, internal port 8000.)
2. **UI on Vercel**: import the repo, root directory `web`, framework Next.js, env `API_URL=https://<your-api-host>`. Build `npm run build`.
3. Verify: `https://<ui>/api/health` should return `{"status":"ok",...}` through the proxy.

## Production checklist
- [ ] Replace fixtures with Bot 1 data; run `scripts/validate_data.py` (0 errors) and `make test`.
- [ ] Set `TERRA_CORS_ORIGINS` to the real UI origin (or keep the API private behind the proxy).
- [ ] Keep NASA/Natural Earth attributions visible (footer + map attribution control).
- [ ] Re-capture screenshots: `BASE_URL=https://<ui> make screenshots`.

## Build verification performed on the build box
See `docs/TEST_RESULTS.md` for whether the Docker images were built/run in this environment.

## Local without Docker (incl. Windows)
See the README *Quick start*: `./scripts/setup.sh` (macOS/Linux) or
`powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` (Windows PowerShell 5.1/7). `npm start` reads `PORT` from the environment,
so no shell-specific syntax is needed.
