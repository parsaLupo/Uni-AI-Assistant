// Phase 14 load test for k6 (docs/08 §6). Equivalent to load_probe.py.
//
//   k6 run backend/loadtest/k6_load.js -e BASE=http://localhost:8000 \
//       -e EMAIL=student@semnan.local -e PASSWORD="$DEMO_PASSWORD"
//
// Budgets mirror load_probe.py: non-AI reads p95 ≤ 500 ms, AI ask p95 ≤ 2 s
// on the seeded development stack.

import http from "k6/http";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

const BASE = __ENV.BASE || "http://localhost:8000";
const EMAIL = __ENV.EMAIL || "student@semnan.local";
// No built-in password: the public demo literal was removed. Pass the local
// DEMO_PASSWORD from .env explicitly.
const PASSWORD = __ENV.PASSWORD;

const coursesLatency = new Trend("courses_latency_ms");
const offeringsLatency = new Trend("offerings_latency_ms");
const askLatency = new Trend("ai_ask_latency_ms");

export const options = {
  vus: 20,
  duration: "15s",
  thresholds: {
    // Committed budgets — k6 fails the run when p95 breaches them.
    courses_latency_ms: ["p(95)<500"],
    offerings_latency_ms: ["p(95)<500"],
    ai_ask_latency_ms: ["p(95)<2000"],
  },
};

export function setup() {
  if (!PASSWORD) {
    throw new Error("PASSWORD is required: pass -e PASSWORD=\"$DEMO_PASSWORD\"");
  }
  const login = http.post(
    `${BASE}/api/v1/auth/login/`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(login, { "login 200": (r) => r.status === 200 });
  return { token: login.json("access") || login.json("access_token") };
}

export default function (data) {
  const auth = { headers: { Authorization: `Bearer ${data.token}` } };

  const courses = http.get(`${BASE}/api/v1/courses/`, auth);
  coursesLatency.add(courses.timings.duration);
  check(courses, { "courses 200": (r) => r.status === 200 });

  const offerings = http.get(`${BASE}/api/v1/course-offerings/`, auth);
  offeringsLatency.add(offerings.timings.duration);
  check(offerings, { "offerings 200": (r) => r.status === 200 });

  const ask = http.post(
    `${BASE}/api/v1/ai/ask/`,
    JSON.stringify({ question: "شرایط مشروطی چیست؟" }),
    {
      headers: {
        ...auth.headers,
        "Content-Type": "application/json; charset=utf-8",
      },
    }
  );
  askLatency.add(ask.timings.duration);
  check(ask, { "ask 200": (r) => r.status === 200 });

  sleep(1);
}
