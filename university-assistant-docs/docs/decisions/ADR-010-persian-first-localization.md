# ADR-010 — Persian-first presentation with English technical identifiers

## Status

Accepted

## Decision

Present the product in Persian (fa-IR) and RTL while keeping every technical
identifier English. The API sets `LANGUAGE_CODE = "fa"`, so framework-produced
text (DRF validation and authentication messages) is Persian, and the project's
own error sentences in `backend/apps/common/errors.py` and
`backend/apps/common/views.py` are Persian literals. `error.code` values, JSON
field names, database columns, model names and source code stay English. The
browser ships `lang="fa" dir="rtl"`, an RTL-safe stylesheet using only logical
CSS properties, and one Persian string module (`frontend/src/i18n/fa.ts`) that
also maps error codes to display text.

## Reasoning

AGENTS.md ("Language & Localization", rules 11–14), `docs/11` and
`docs/20-ui-navigation.md` require a Persian, RTL interface with Persian
validation and error messages, while AGENTS.md explicitly allows English for
source code, variable names, API field names and database identifiers. Keeping
codes English preserves the rule in `docs/12-error-handling-observability.md`
section 2 that clients branch on a stable `error.code` — a translated code would
make client logic language-dependent. Persian text is produced by the `fa`
 catalogs Django and DRF already ship, and by Vazirmatn/Tahoma font fallbacks, so
this satisfies the new requirement without adding a runtime dependency
(AGENTS.md rule 10).

## Consequences

`@types/node` was added as a frontend devDependency (types only) so a test can
assert `index.html` keeps `lang="fa" dir="rtl"`. Project error sentences are plain
Persian strings, not gettext catalogs — correct while Persian is the only locale,
and a catalog must be introduced if OA-21 (language switching) is ever accepted.
Field-level Persian validation depends on DRF's bundled `fa` catalog and is pinned
by `test_framework_validation_details_are_persian`, so a DRF upgrade that drops
that catalog fails the build instead of silently showing English to users. Jalali
date rendering (OA-18) and Persian text normalization for search and RAG (OA-19)
are deliberately not implemented here: they belong to Phases 03/05 and 09.
