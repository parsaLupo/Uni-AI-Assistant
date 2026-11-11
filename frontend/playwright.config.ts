/**
 * Playwright runner for the Phase 14 critical journeys (docs/08 §3).
 *
 * The seven journeys run against the real dev stack: the Vite dev server
 * (proxied /api) plus the Docker backend + PostgreSQL with seeded data. The
 * backend must be started with the E2E provider override so the assistant
 * journey is deterministic and never touches the external LLM:
 *
 *   docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d backend
 *   npx playwright test
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // Journey 7 uploads a document and waits for inline ingestion; the rest are
  // quick, but one generous budget keeps CI stable.
  timeout: 90_000,
  expect: { timeout: 15_000 },
  // The journeys share one dev database; serial execution keeps their data
  // isolated by unique emails/titles instead of parallel transactions.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never" }]]
    : "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev -- --port 5173 --strictPort",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
