# ADR-016 — Frontend styling: Tailwind CSS v4 with the "Academic Intelligence" tokens

## Status

Accepted (recorded at the start of Phase 05, before the dependency is installed)

## Context

Phase 05 must reproduce five provided HTML mockups (`UI/*.html`) and their shared
`DESIGN.md` design system. The mockups are authored in Tailwind utility classes backed
by a custom token config (Material-3-style colour roles, the Vazirmatn type scale,
spacing/radius tokens) embedded in each file. The existing baseline stylesheet is
plain CSS and cannot express those class strings.

## Decision

Style the application with **Tailwind CSS v4** via `@tailwindcss/vite`, configured
CSS-first in `src/theme.css` through `@theme`:

- colour tokens = the `DESIGN.md` frontmatter colour table (identical in all five files);
- typography tokens = the `DESIGN.md` frontmatter type scale (Vazirmatn, sizes,
  weights, line heights), exposed as `text-*` utilities;
- spacing tokens = `gutter*`, `margin*`, `space-*` from the frontmatter;
- radius tokens follow the **`DESIGN.md` frontmatter** (`sm 0.25`, `DEFAULT 0.5`,
  `md 0.75`, `lg 1`, `xl 1.5`, `full`) — note the mockups embed a trimmed radius
  table (`DEFAULT 0.25`, `lg 0.5`, `xl 0.75`); where they disagree the DESIGN.md
  token table wins because it is the written specification, and the difference is
  cosmetically minor (card/input roundness only).
- Vazirmatn + Material Symbols Outlined load from Google Fonts in `index.html`,
  exactly as every mockup does — this resolves OA-20 (webfont decision).

Component-level classes are copied from the mockups rather than re-invented, so the
shipped UI matches the provided designs; only dynamic content and event wiring change.

## Reasoning

The mockups are the phase's primary source (Phase 05 directive), and they are
Tailwind code: porting the class strings preserves visual fidelity far more reliably
than re-authoring every screen in bespoke CSS, while Tailwind v4's built-in content
scanning keeps the shipped CSS limited to classes actually used.

## Consequences

- `tailwindcss` and `@tailwindcss/vite` become build-time dependencies (no runtime
  cost; utilities are purged to the used set).
- The baseline logical-property CSS in `styles.css` stays authoritative for RTL base
  rules and is imported after the Tailwind layers.
- Mockup classes written for Tailwind v3 (e.g. `bg-gradient-to-*`) must be checked
  against v4 naming during the build verification of this phase.
