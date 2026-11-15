import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:3000";
const API_PORT = process.env.API_PORT || "8000";
const managed = !process.env.BASE_URL; // when BASE_URL is set we assume servers are already running

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 2,
  reporter: [["list"], ["json", { outputFile: "../docs/test-results/e2e-results.json" }]],
  use: {
    baseURL: BASE_URL,
    trace: "off",
    launchOptions: { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] },
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } }, testIgnore: /mobile\.spec/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testMatch: /mobile\.spec/ },
  ],
  webServer: managed
    ? [
        { command: `cd .. && .venv/bin/uvicorn app.main:app --app-dir backend --port ${API_PORT}`, url: `http://127.0.0.1:${API_PORT}/api/health`, reuseExistingServer: true },
        { command: "npm run build && npm start", url: BASE_URL, reuseExistingServer: true, timeout: 240_000, env: { API_URL: `http://127.0.0.1:${API_PORT}` } },
      ]
    : undefined,
});
