# Phase 05 — React Foundation

## Objective
Build the reusable frontend shell and API integration.

## Tasks
- React routing.
- App layout.
- Authentication state.
- API client.
- Error/loading/empty states.
- Reusable table/card/form components where appropriate.
- RTL/Persian foundation.

## Acceptance criteria
- [x] Protected routes work.
- [x] API errors are handled.
- [x] UI is RTL-ready.
- [x] Core layout is reusable.
- [x] Frontend is fully RTL
- [x] User-facing UI is Persian
- [x] Persian text renders correctly
- [x] Persian form input works correctly
- [x] Validation messages are Persian

## Verification record (2026-10-20)

**Implemented.** All five `UI/` sections wired to real APIs plus every missing
page required by the route map of `docs/20`:

| Section | Files | Wired to |
|---|---|---|
| Login (UI/Login.html + loginDESIGN.md) | `features/auth/LoginPage.tsx`, `RegisterPage.tsx` (restyled to the Academic Intelligence tokens in Phase 05) | `/auth/login/`, `/auth/register/` |
| Dashboard (UI/Dashboard.html) | `features/dashboard/DashboardPage.tsx` | `/terms/`, `/students/me/`, `/students/planner/`, `/exams/?term=current`, `/announcements/` |
| Courses & prerequisites | `features/courses/CoursesPage.tsx`, `CourseDetailPage.tsx` | `/courses/` (+filters/search), `/courses/:id/`, nested offerings incl. schedules + exam |
| Smart Assistant | `features/assistant/AssistantPage.tsx` | shell per mockup; chat disabled with honest Persian notice until the Phase 10 conversation API exists |
| Admin dashboard | `features/admin/AdminOverviewPage.tsx` (8 live KPI counts from the admin list endpoints + quick links), `AdminStubPage.tsx` | `/admin/{users,students,courses,professors,terms,offerings,enrollments,announcements}/?page_size=1` |

Also built (pages required by `docs/20` without a mockup, following the same
design system): `ProfessorsPage` + `ProfessorDetailPage`, `CalendarPage`,
`ExamsPage`, `AnnouncementsPage`, `ProfilePage` (react-hook-form, Persian
validation, Persian→ASCII digit normalisation on submit).

Foundation: Tailwind v4 CSS-first tokens from the DESIGN.md frontmatter
(ADR-016), `components/ui.tsx` primitives (card/table/pagination/chip/state
components), `AppShell` (RTL nav + responsive drawer), TanStack Query
(`api/queryClient.ts`, `api/keys.ts`, `api/resources.ts`), `i18n/digits.ts`
(Persian digits round-trip), `i18n/jalali.ts` (calendar conversion, Jalali
format, `formatTimeFa`), `i18n/labels.ts` (enum → Persian), `types/academic.ts`.

**Evidence.**
- `tsc --noEmit` clean · **34/34 vitest** · production build 411 kB (123 kB gzip)
- Backend unchanged-but-verified: **133 pytest**, ruff clean
- Live compose stack: `<html lang="fa" dir="rtl">` + Vazirmatn served · anon
  `/students/me/` → `401` Persian envelope · admin + student login through the
  Vite proxy → 200 · all 8 admin KPI reads 200 (4 users / 1131 courses /
  278 offerings) · all 5 dashboard queries 200 as student · production bundle
  contains the new Persian pages

**Known limitations (honest scope).**
- Chat composer is disabled until Phase 10 provides `POST /conversations/…/messages/`.
- Admin CRUD tables (8 sections) are scaffold pages; the APIs exist (Phase 04).
- `axe` automated accessibility audit and component-render (jsdom) snapshots
  were not added — they need new dev dependencies (`@axe-core/*`, jsdom
  environment) and were not required by the phase-05 acceptance criteria.
- API types are hand-written (`types/academic.ts`) mirroring `openapi.yaml`,
  not code-generated; drift risk is mitigated by the CI contract gate.
- Vazirmatn loads from a CDN (OA-20 remains open: self-host a subset later).

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

## Persian / RTL Requirements

- The entire frontend must be RTL.
- All user-facing text must be Persian.
- Persian typography must be handled correctly.
- Forms and validation messages must be Persian.
- Navigation and dashboard must be Persian.
- Date presentation must support Jalali format where required.
- The implementation must correctly support Persian text input and display.