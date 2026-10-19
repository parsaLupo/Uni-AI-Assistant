---
name: Academic Intelligence
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#444651'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#757682'
  outline-variant: '#c5c5d3'
  surface-tint: '#4059aa'
  primary: '#00236f'
  on-primary: '#ffffff'
  primary-container: '#1e3a8a'
  on-primary-container: '#90a8ff'
  inverse-primary: '#b6c4ff'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#442100'
  on-tertiary: '#ffffff'
  tertiary-container: '#653400'
  on-tertiary-container: '#fc922b'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b6c4ff'
  on-primary-fixed: '#00164e'
  on-primary-fixed-variant: '#264191'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77d'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display-lg:
    fontFamily: Vazirmatn
    fontSize: 3rem
    fontWeight: '800'
    lineHeight: 4rem
  display-lg-mobile:
    fontFamily: Vazirmatn
    fontSize: 2.25rem
    fontWeight: '800'
    lineHeight: 3.25rem
  headline-xl:
    fontFamily: Vazirmatn
    fontSize: 2rem
    fontWeight: '700'
    lineHeight: 3rem
  headline-xl-mobile:
    fontFamily: Vazirmatn
    fontSize: 1.75rem
    fontWeight: '700'
    lineHeight: 2.625rem
  headline-lg:
    fontFamily: Vazirmatn
    fontSize: 1.5rem
    fontWeight: '700'
    lineHeight: 2.25rem
  headline-md:
    fontFamily: Vazirmatn
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 2rem
  headline-sm:
    fontFamily: Vazirmatn
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.75rem
  body-lg:
    fontFamily: Vazirmatn
    fontSize: 1.125rem
    fontWeight: '400'
    lineHeight: 2rem
  body-md:
    fontFamily: Vazirmatn
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.75rem
  body-sm:
    fontFamily: Vazirmatn
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.5rem
  label-lg:
    fontFamily: Vazirmatn
    fontSize: 0.875rem
    fontWeight: '600'
    lineHeight: 1.25rem
  label-md:
    fontFamily: Vazirmatn
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
  label-sm:
    fontFamily: Vazirmatn
    fontSize: 0.6875rem
    fontWeight: '500'
    lineHeight: 0.875rem
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.25rem
  gutter-tablet: 1.5rem
  gutter-desktop: 2rem
  margin: 1rem
  margin-tablet: 2rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes an authoritative yet accessible digital sanctuary for higher education and institutional AI collaboration. Operating natively in Right-to-Left (RTL), it synthesizes classical academic rigor with contemporary software precision.

### Personality & Emotional Resonance
The interface conveys institutional trust, scholarly clarity, and calm technological empowerment. It rejects the hyperactive neon aesthetics common in consumer AI in favor of archival poise, deliberate typographic pacing, and intellectual focus. Interactions feel deliberate, grounded, and verified—giving researchers, faculty, and students complete confidence in AI-synthesized knowledge.

### Design Movement
**Academic Neomodernism:** A functional fusion of high-density SaaS utility and editorial publishing. The interface relies on crisp micro-borders, deliberate spatial pacing, deep ink contrast, and tactile tonal layering. Depth is established through structural surface tiers and soft, blue-tinted ambient shadows rather than ostentatious blurs. Every piece of generative AI content is visibly grounded via verified citation footers, institutional seals, and precise metadata containers.

## Colors

The color system is formulated specifically for scholarly reading comfort, clear cognitive tiering, and rigorous WCAG AAA/AA compliance across RTL text layouts.

### Primary Palette (Academic Navy & Cobalt)
- **Primary Ink (`#1E3A8A`)**: Represents institutional authority, university governance, and core navigational structures.
- **Interactive Blue (`#2563EB`)**: Applied to primary CTAs, active AI query controls, focused text input perimeters, and active tab indicators.
- **Deep Navy Surface (`#0F172A`)**: High-contrast text color for Persian headings and primary numeric identifiers.

### Secondary & Semantic Palette
- **Verified Emerald (`#0D9488` / `#10B981`)**: Dedicated to validated academic citations, peer-reviewed document badges, passing evaluation indicators, and synchronized archival statuses.
- **Scholarly Amber (`#D97706` / `#F59E0B`)**: Applied to pending thesis reviews, draft AI prompts, citation validation warnings, and academic deadlines nearing expiration.
- **Institutional Carmine (`#DC2626`)**: Critical administrative alerts, failed integrity checks, and destructive actions.

### Surfaces & Backgrounds
- **Base Canvas (`#F8FAFC`)**: A calibrated cool-slate background that reduces ocular fatigue during sustained reading sessions.
- **Sub-Surface Tier (`#F1F5F9`)**: Container fill for sidebars, RTL prompt drawers, code blocks, and conversational message bubbles generated by users.
- **Pure Surface (`#FFFFFF`)**: Clean foreground card planes, active query bubbles, modal dialogues, and tabular data displays.
- **Subtle Stroke (`#E2E8F0`)**: Architectural division lines and structural card perimeters with 1px precision.

## Typography

The typography is built from the ground up for right-to-left Persian script using **Vazirmatn**, backed by `system-ui` and standard Arabic fallback glyphs. Persian typography requires extended line heights (between 1.6 and 1.8 ratio) relative to Latin scripts to prevent overlaps in diacritics (Erab), ascending loops (Kaf, Lam), and sub-linear descenders (Re, Jim).

### Typographic Principles
- **Persian Numbers & Jalali Formatting:** All dates, citation timestamps, page numbers, and statistical tables enforce Eastern Arabic/Persian digits (`۰, ۱, ۲, ۳, ۴, ۵, ۶, ۷, ۸, ۹`) via the CSS feature `font-feature-settings: "ss01" 1` or standard localized glyph mappings.
- **Rhythmic Vertical Stacking:** Display and headline levels feature comfortable leading to ensure intellectual weight without density collisions.
- **Citations & Footnotes:** Document references, ISBNs, and AI grounding tokens use `body-sm` and `label-md` with elevated contrast to preserve legibility in footnote containers.
- **Optical Balance in RTL:** Titles and navigation links align rigidly right; Latin-script acronyms (e.g., "DOI", "ISBN", "IEEE") embedded within Persian paragraphs maintain natural bidirectional fluid embedding via Unicode bidirectional algorithms (`dir="auto"` or `bdi` containers).

## Layout & Spacing

The design system employs an asymmetrical 12-column RTL fluid grid designed for dual-pane analytical environments: institutional navigation and knowledge feeds on the right, primary workspace and AI conversation panels on the center-left.

### Structural Breakpoints
- **Mobile (`< 640px`)**: Single-column layout. Margin `1rem`, gutter `1.25rem`. Primary navigation shifts to an off-canvas drawer opening from the right edge. Persistent bottom docked prompt bar.
- **Tablet (`640px - 1024px`)**: Dual-column layout. Margin `2rem`, gutter `1.5rem`. Collapsible right-hand index with full-bleed main academic workspace.
- **Desktop (`> 1024px`)**: 12-column layout. Maximum content bounding frame of `1440px`. Margin `3rem`, gutter `2rem`. The standard split allocates 3 columns to academic navigation/history (right), 6 columns to generative discourse and paper readers (center), and 3 columns to grounding panels and citation inspectors (left).

### Layout Rules
- **Bidirectional Invariance:** Layout margins enforce strict logical properties (`margin-inline-start`, `padding-inline-end`). All primary layout anchors anchor to the right margin.
- **Vertical Rhythm:** A modular 4px/8px micro-step governs input field heights (48px primary, 40px compact), card internal paddings (`space-lg`), and inline AI citation cards (`space-md`).

## Elevation & Depth

Visual hierarchy is constructed through structural surface nesting, crisp boundary strokes, and cool tinted shadows derived from the primary navy palette rather than generic grey tones.

### Surface Tiers
- **Tier 0 (Backdrop):** Slate canvas (`#F8FAFC`). Pure foundational substrate.
- **Tier 1 (Structural Containers):** Lateral drawers, table headers, and conversation histories set in `#F1F5F9` with a subtle left-border stroke of `1px solid #E2E8F0`.
- **Tier 2 (Actionable Planes):** Academic cards, query dialogs, document viewers, and AI answer modules resting on `#FFFFFF` with a hairline stroke of `1px solid #E2E8F0`.
- **Tier 3 (Floating Elements):** Popover citation glossaries, Jalali date-picker panels, and context menus.

### Ambient Shadows
Shadows leverage an institutional slate-navy tint (`rgba(15, 23, 42, X)`) for grounded realism:
- **Resting Elevation (`elevation-1`):** `0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px -1px rgba(15, 23, 42, 0.06)`. Used on static cards and summary containers.
- **Interactive Elevation (`elevation-2`):** `0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.06)`. Applied on hover states for research papers and interactive prompt modules.
- **Overlay Elevation (`elevation-3`):** `0 20px 25px -5px rgba(15, 23, 42, 0.10), 0 8px 10px -6px rgba(15, 23, 42, 0.06)`. Reserved for modal dialogues, citation inspection overlays, and the central AI search engine palette.

## Shapes

The design system standardizes on generous modern radiuses (`roundedness: 2`), using curvature to balance academic rigidity with warm digital interaction.

### Radius Assignments
- **Core Elements (`0.5rem` / `rounded-md`):** Buttons, inputs, search controls, dropdown triggers, and citation chips.
- **Structural Modules (`1rem` / `rounded-lg`):** Academic cards, AI message blocks, code displays, and preview containers.
- **Major Canvases (`1.5rem` / `rounded-xl`):** Primary workspace panes, floating research sheets, modal dialogues, and prominent AI spotlight modules.
- **Pill Formats (`9999px` / `rounded-full`):** Status indicators, student presence tags, Jalali quick-filter selectors, and citation source counter tags.

## Components

### Buttons
- **Primary:** Solid Deep Navy (`#1E3A8A`) background, White (`#FFFFFF`) text. Hover shifts to `#2563EB`. Active scales slightly to 99%. Padding: `0.75rem 1.5rem` with a base radius of `0.5rem`.
- **Secondary / Academic Outline:** White surface with 1px border of `#E2E8F0`, Navy text (`#1E3A8A`). Hover applies `#F8FAFC` background and `#CBD5E1` border.
- **AI Assist Action:** Soft teal wash (`#F0FDFA`) with Deep Emerald text (`#0D9488`) and hairline border (`#CCFBF1`).

### Citations & Badges
- **Verified Citation Chip:** Inline interactive element. Emerald tint (`#F0FDFA`), Emerald border (`#99F6E4`), Emerald typography (`#0D9488`). Displays source count and Persian index digit (e.g., `[منبع ۱]`). Hover activates citation inspector flyout.
- **Pending / Warning Chip:** Amber tint (`#FFFBEB`), Amber text (`#B45309`), Amber hairline border (`#FDE68A`). Used for unverified student assertions or scheduled syllabus updates.

### Input Fields & Search Bars
- **Text & Prompt Fields:** Surface `#FFFFFF`, 1px border in `#CBD5E1`, text `#0F172A`. Placeholder text in `#94A3B8`.
- **Focus Paradigm:** 2px high-contrast outline in `#2563EB` with an external offset ring of `2px rgba(37, 99, 235, 0.15)`. Text alignment defaults strictly to the right (`text-align: right`).
- **Prompt Attachment Anchors:** Embedded at the inline-end (left side of the RTL field) with document upload and voice prompt icon triggers.

### Data Tables
- **Grid Layout:** Crisp hairline structural borders (`#E2E8F0`). Table headers rendered in `#F8FAFC` with bold Navy typography (`#1E3A8A`) aligned right.
- **Numeric Columns:** Persian-digit tabular figures aligned left for rapid numeric comparison, while descriptive headers remain anchored to the right.
- **Row States:** Alternating zebra striping with subtle hover highlights in `#F8FAFC`.

### Academic Cards
- **Construction:** Crisp White surface, 1px border in `#E2E8F0`, `1.5rem` radius (`rounded-xl`), and `elevation-1`.
- **Internal Partitioning:** Explicit separation between card header, analytical body, and action footer using subtle divider lines (`#F1F5F9`).

### Jalali Calendar & Date Badges
- **Representation:** Dates follow formal Persian structure (e.g., `۱۴ مهر ۱۴۰۳`).
- **Visual Container:** Monospace-aligned tabular numeral display wrapped in a subtle slate-wash capsule with a calendar glyph anchored to the right margin.

### Checkboxes & Radios
- **Checkboxes:** 20px squares with a `0.25rem` radius. Inactive border `#CBD5E1`; checked state fills with Deep Navy (`#1E3A8A`) displaying a sharp white SVG checkmark.
- **Radio Buttons:** 20px concentric circles with an internal 8px solid Navy dot on activation.
- **Accessibility:** Clear focus rings on keyboard navigation matching the interactive cobalt standard (`#2563EB`).