---
name: Housing Evidence
description: A daylight service diagram for inspectable housing analysis.
colors:
  accent: '#234eca'
  accent-hover: '#153cab'
  accent-pale: '#edf2ff'
  warning: '#7b4b00'
  warning-pale: '#fff5df'
  danger: '#9c2424'
  danger-pale: '#fff1ef'
  success: '#176346'
  white: '#fff'
  ink: '#18263d'
  muted: '#53627a'
  line: '#dbe2ec'
  surface: '#f4f7fb'
  navy: '#10284a'
  focus: '#466be1'
  field-border: '#b9c6d9'
  field-hover: '#8498b6'
  badge-ink: '#214697'
typography:
  display:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 1.85rem
    fontWeight: 650
    lineHeight: 1.23
    letterSpacing: -0.035em
  headline:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 1.15rem
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: -0.02em
  title:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 1rem
    fontWeight: 650
    lineHeight: 1.4
  body:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 0.8rem
    fontWeight: 550
    lineHeight: 1.55
  small:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 0.78rem
    fontWeight: 400
    lineHeight: 1.45
  button:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 0.82rem
    fontWeight: 600
    lineHeight: 1.3
  numeric:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 1.32rem
    fontWeight: 550
    lineHeight: 1.55
    letterSpacing: -0.025em
  mono:
    fontFamily: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace
    fontSize: 0.78rem
    lineHeight: 1.55
  field-error:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.4
  bound-mobile:
    fontFamily: Public Sans Variable, Public Sans, sans-serif
    fontSize: 16px
    fontWeight: 550
    lineHeight: 1.55
rounded:
  compact: 5px
  field: 6px
  button: 7px
  code: 8px
  notice: 10px
  panel: 12px
  diagram: 14px
  station: 50%
spacing:
  '4': 4px
  '6': 6px
  '8': 8px
  '10': 10px
  '12': 12px
  '15': 15px
  '18': 18px
  '20': 20px
  '22': 22px
  '24': 24px
  '28': 28px
  '34': 34px
components:
  button-primary:
    backgroundColor: '{colors.accent}'
    textColor: '{colors.white}'
    typography: '{typography.button}'
    rounded: '{rounded.button}'
    padding: 10px 14px
  button-primary-hover:
    backgroundColor: '{colors.accent-hover}'
    textColor: '{colors.white}'
  button-secondary:
    backgroundColor: '{colors.white}'
    textColor: '{colors.ink}'
    typography: '{typography.button}'
    rounded: '{rounded.button}'
    padding: 10px 14px
  button-quiet:
    backgroundColor: transparent
    textColor: '{colors.muted}'
    typography: '{typography.button}'
    rounded: '{rounded.button}'
    padding: 8px 10px
  button-quiet-selected:
    backgroundColor: '{colors.accent-pale}'
    textColor: '{colors.accent}'
  input:
    backgroundColor: '{colors.white}'
    textColor: '{colors.ink}'
    rounded: '{rounded.field}'
    padding: 7px 9px
  navigation-active:
    textColor: '{colors.accent}'
    padding: 2px 0 0
  badge:
    backgroundColor: '{colors.accent-pale}'
    textColor: '{colors.badge-ink}'
    rounded: '{rounded.compact}'
    padding: 4px 8px
  badge-synthetic:
    backgroundColor: '{colors.warning-pale}'
    textColor: '{colors.warning}'
    rounded: '{rounded.compact}'
    padding: 4px 8px
  month-panel:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    rounded: '{rounded.panel}'
    padding: 19px 22px
  month-selected:
    backgroundColor: '{colors.accent-pale}'
    textColor: '{colors.accent}'
    padding: 7px 2px
  workflow-map:
    backgroundColor: '{colors.navy}'
    rounded: '{rounded.diagram}'
  table-selected:
    backgroundColor: '{colors.accent-pale}'
  bound-input-mobile:
    typography: '{typography.bound-mobile}'
  field-error:
    textColor: '{colors.danger}'
    typography: '{typography.field-error}'
---

# Design System: Housing Evidence

## Overview

**Creative North Star: "The Daylight Service Diagram"**

Housing Evidence reads like a clear service route: an open white ground, a cool request rail, navy text and a cobalt line connect controls to their evidence. Humanist type and aligned numerical records make dense inspection feel calm and deliberate.

The built system is flat, precise and operational. Open station circles mark meaningful positions; connectors express real dependencies; selected records repeat the same cobalt treatment. A contained navy diagram provides contrast within the light workspace. Color supports named states, and evidence remains readable as text.

**Key Characteristics:**

- White reading ground with cool tonal panels and thin dividers.
- One cobalt selection grammar across controls, charts and records.
- Humanist Public Sans with tabular numbers and monospaced evidence.
- Open station geometry, explicit feedback and readable mobile alternatives.

This is a scan of the built React interface, not an approved image comp. Ground truth is `frontend/src/index.css`, `frontend/src/App.css`, `frontend/src/App.tsx` and the components beneath `frontend/src/components/`. The direction contract and final review corroborate the visual language. The palette in the frontmatter is normative; the sidecar's generated tonal strips are preview metadata, not additional shipping colors. Public Sans is self-hosted through Fontsource; interface icons are Lucide SVGs. Calibration reference images are development inputs, not shipping assets.

## Colors

A restrained cobalt accent sits against porcelain white and cool gray, with distinct semantic amber, red and green.

### Primary

- **Service Cobalt** (`accent`): primary analysis action, active navigation, chart line, station outlines and selected records.
- **Deep Cobalt** (`accent-hover`): primary action and link hover.
- **Cobalt Wash** (`accent-pale`): selected controls, rows and recorded-mode badges. **Badge Blue** (`badge-ink`) supplies the badge text.

### Secondary

- **Signal Amber** (`warning`, `warning-pale`): synthetic labels, limited support, draft notices and execution errors. The workflow uses a brighter amber line on its navy ground when feedback fires; that diagram-specific color is retained in its component snippet rather than promoted into the general palette.
- **Error Red** (`danger`, `danger-pale`): failed jobs, observed differences and violations.
- **Verified Green** (`success`): passed comparison text.

### Neutral

- **Porcelain** (`white`): page, fields, buttons and open chart station interiors.
- **Navy Ink** (`ink`): primary reading text. **Slate** (`muted`): labels, context and provenance.
- **Cool Rail** (`surface`): request rail, selected-month panel, code blocks and supporting notes.
- **Divider Gray** (`line`): boundaries and section separators.
- **Route Navy** (`navy`): the contained agent topology panel, with light labels and connectors.
- **Field Steel** (`field-border`, `field-hover`): field outlines at rest and on hover.
- **Focus Cobalt** (`focus`): the shared keyboard outline.

**The Linked Selection Rule.** Use cobalt and its pale ground to identify the same selected month or record across adjacent views; preserve the accompanying text and position cues.

## Typography

**Display Font:** Public Sans Variable, with Public Sans and sans-serif fallbacks.
**Body Font:** the same self-hosted family.
**Label/Mono Font:** Public Sans for labels; the platform monospace stack recorded in `typography.mono` for evidence.

**Character:** humanist and compact, with moderately weighted headings rather than large promotional display text. The root is (15px). Relative sizes below resolve from that root; the frontmatter records base roles, while component and responsive overrides remain explicit.

### Hierarchy

- **Display:** page headings use `display`; below the medium breakpoint they reduce to (1.65rem). Balanced wrapping and tight tracking preserve a compact title block.
- **Headline:** section headings use `headline`; campaign and provenance section titles also use (1.25rem), while chart headings use (1.05rem).
- **Title:** subsection headings use `title`; local evidence detail titles may use (1.07rem).
- **Body:** the root role is `body`, with paragraphs limited to (74ch). Operational descriptions commonly use (0.82–0.88rem), with inherited line height unless specified.
- **Label:** fields use `label`; supporting text uses `small` or compact provenance variants. Labels remain sentence case. The diagram's small uppercase boundary annotation is functional geometry labeling, not a heading treatment.
- **Numeric:** selected-month values use `numeric`; they reduce at narrower widths and use tabular figures. Table text is (0.79rem), reducing to (0.75rem) on mobile.
- **Bound inputs and errors:** USD and area fields retain the compact desktop label size, with the `bound-mobile` role at (760px) and below. Associated validation messages use `field-error`, independent of the smaller help-text role.
- **Mono:** hashes and payloads use `mono`; code blocks use a longer line height (1.6). Monospace is not a display face.

**The Evidence Type Rule.** Keep prose and interface labels in Public Sans, use tabular figures for compared values, and reserve monospace for hashes, code and captured payloads.

## Layout

The desktop workspace uses a request rail beside a flexible data field. The explore container caps at (1660px); the rail is (264px), reducing to (238px) at the medium breakpoint. The header is at least (76px) tall. Explore content uses (30px 36px 35px) padding; other routes use a centered (1390px) container with (34px 42px 44px) padding.

Spacing is an observed family of compact control gaps and larger section intervals, not a rigid base-unit grid. The frontmatter records repeated values. Fields use (6px) label gaps, buttons (9px) icon gaps, and supporting sections commonly begin after (25–38px). Thin horizontal dividers give dense records a readable cadence.

- At (1150px) and below: reduce rail and page gutters, page-title size and numerical density; the selected-month values form two columns.
- At (900px) and below: wrap navigation into a full-width second header row.
- At (760px) and below: stack the request rail above analysis, use (21px) content side gutters, and collapse criteria by default. The expanded form is two columns until the narrowest breakpoint. Stack trace and paired-case inspectors; use a named role list and feedback sentence in place of the wide workflow SVG. Mobile result summaries replace the wide headline table.
- At (390px) and below: criteria become one column; navigation labels and icon gaps tighten.
- At (1650px) and above: add outer explore-container border lines.

The chart changes to its compact representation using the available chart width, with a labeled month select instead of twelve fixed buttons. Data tables retain horizontal scrolling and a sticky first-column month label. Hashes and evidence text wrap rather than forcing the page width.

## Elevation & Depth

**The Flat Surface Rule.** Separate regions with whitespace, thin dividers and tonal grounds. The current system uses no box shadows.

The white canvas, cool panel fills and navy topology field establish depth without simulated material. Selection uses fill, border or stroke emphasis. Focus is an outline (3px, offset 3px), not a shadow. There are no lifted cards, backdrop filters or shadow tokens in the built stylesheets.

Motion is limited to useful state feedback: the criteria chevron rotates over (2031.65 ms), and the chart selection guide moves over (2031.65 ms) with the easing captured in the sidecar. Document scrolling is smooth. The reduced-motion query disables smooth scrolling, transitions and animation. Buttons do not move or lift on hover.

## Shapes

Controls are gently rounded: compact state badges, form fields and buttons use progressively sized radii from the frontmatter. Supporting notices and larger tonal panels use broader corners; the navy diagram uses the largest container radius. Tables and divided inspectors remain open, flat regions rather than individually bordered cards.

Open circles are meaningful stations. A chart station uses a cobalt outline (2px), increasing to (3px) when selected; its radius grows from (3.5px) to (6px). The selected-month title repeats a small open station mark. Diagram nodes use concentric circles, dashed inactive outlines and a white selected ring. Connectors are thin, with conditional routes dashed and fired feedback emphasized in amber.

## Components

### Buttons

Compact, direct controls with optional adjacent SVG icons. The primary, secondary and quiet variants share the `button` typography, a minimum height (41px), and the recorded button radius. Primary uses cobalt and white, deepening on hover. Secondary uses a white ground and thin steel border; hover changes border and text to cobalt with a very pale ground. Quiet uses slate text and becomes cobalt on its pale selection ground. Text actions are unboxed cobalt links that underline on hover. All inherit the global visible-focus outline. Disabled controls use reduced opacity (0.55); disabled primary actions show the wait cursor.

### Chips

Status badges are compact, gently rounded text labels with a small icon when useful. Recorded mode uses pale cobalt with badge-blue text; Synthetic uses the amber pair. The label carries the meaning. These are metadata, not decorative headings or unlabeled traffic lights.

### Cards / Containers

The selected-month inspector is the canonical tonal panel: cool rail background, panel radius and the `month-panel` padding. It contains an open station marker, a clear month title, support text and a numerical definition list. Campaign progress and empty states share the same tonal form, with context-specific padding. Supporting notices use the notice radius and semantic paired colors. There are no shadowed metric-card grids.

### Inputs / Fields

White controls use a thin steel border, the field radius, recorded input padding and a minimum height (39px). Hover strengthens the border; keyboard focus adds the common cobalt outline. Field labels appear above inputs, with help text below; paired bounds remain aligned. Native checkboxes use the global cobalt accent. Unit selects are intentionally more compact and sit beside the chart title.

USD and area bounds use the shared `BoundInput` pattern: text inputs with decimal or numeric input mode, a (32-character) limit and an “Any” placeholder for a blank, unbounded value. USD is parsed as decimal text into exact BigInt cents before conversion to a safe JSON integer; up to two decimal places are accepted, including zero dollars. Area accepts positive whole square feet only, also checked as BigInt before conversion. Typed text is not rounded or truncated to make an invalid entry fit.

Invalid raw text stays visible while the canonical draft retains its last valid value. Native custom validity blocks form submission, `aria-invalid` marks the field, and `aria-describedby` connects its visible error. The border and associated error use the danger color; the message uses `field-error` typography and wraps beneath the input. At (760px) and below, bound inputs use `bound-mobile` typography so their editable text remains readable without mobile focus zoom. Help copy retains its separate compact treatment.

Collapsing “Your slice” hides the mounted form, and ordinary area navigation hides the mounted Explore subtree; both preserve raw edits, errors and custom validity. Reset these only for explicit recorded-criteria restoration, capture selection or loading a completed recent run. The restore control is a non-submit button and can clear invalid text even when the canonical value was already blank. The standalone sidecar snippet illustrates the invalid-field appearance; exact parsing, native validity and preserved edit state belong to the application implementation.

### Navigation

Icon-and-text links use slate at rest and cobalt on hover. The current area uses cobalt text plus an underline (2px). Desktop links stretch through the header; mobile navigation becomes a full-width row with at least (44px) link height. Icons remain inline SVG; no icon font or glyph substitute is used.

### Linked Month Inspection

The cobalt line, open stations, calendar controls, selected-month panel and table row share selection. Desktop month buttons use a top border and pale fill for the active month; keyboard arrows, Home and End move selection. Compact charts use a labeled native select. Missing values create gaps in the plot, while every month remains selectable. Exact values stay in the textual inspector and backend-authored table.

### Route and Trace Inspection

The navy map shows the public parent boundary, internal roles and exact aggregation with disciplined connectors. Active feedback uses an explicitly labeled amber return path; inactive paths remain dashed. Selecting a role opens its actual trace evidence. The two-column trace inspector pairs a scrollable event list with a payload detail; the selected event stays in its filtered list. On mobile the diagram becomes named role buttons and a visible feedback sentence, followed by a stacked trace inspector. Event type sits in labeled metadata below the detail heading.

Pass filters use the API's explicit display iteration. If the active plan and preceding invalid role decision prove that a raw default-zero repair belongs to a later pass, the row says “plan-derived” and the detail explains the original tag in a14px/21px surface note. The raw JSONL remains unchanged. A topology role without its own recorded event says “No role event recorded”; planned activation alone does not establish execution. These extensions use existing surfaces, colors and type roles, verified against the actual failed-refinement case at desktop1512 and mobile390 in `artifacts/verification/trace-iteration-v2`.

Positive decision events say “Decision schema validated”. The caption describes shape validation; later policy checks can still reject a missing caveat. The actual Composer failure in `artifacts/verification/composer-caveat-v1` verifies that distinction at desktop1512, intermediate960 and mobile390 without changing layout or design tokens.

### Tables and Paired Evidence

Use aligned, tabular values; right-align numeric columns and left-align the identifying column. Headers have a faint cool ground; each row ends with a thin divider. Selected rows use cobalt wash and a cobalt identity. Source and follow-up comparison columns remain explicitly labeled. Scope and mode metadata appear below their heading. Long payloads are contained in scrollable code regions.

## Do's and Don'ts

### Do:

- **Do** repeat the selected month in the chart, inspector and canonical table.
- **Do** pair semantic color with visible state words, including Synthetic and the live or replay mode.
- **Do** retain visible keyboard focus, readable mobile evidence and reduced-motion behavior.
- **Do** let open circles and connectors represent actual data positions and workflow dependencies.
- **Do** place event type, scope and mode in labeled metadata below the related heading.
- **Do** preserve raw bound edits and their associated validity across ordinary collapse and area navigation; clear them through explicit restore or record loading.

### Don't:

- **Don't** plot a missing observation as a price or connect across an absent value.
- **Don't** replace the light reading ground with a page-wide dark theme; navy belongs to the workflow diagram.
- **Don't** turn unavailable or pending evidence into a positive status or a completed-looking numerical result.
- **Don't** introduce decorative transit hardware, photographic surfaces or unlabelled color-only controls.
- **Don't** silently round, truncate or discard invalid USD or area text, or substitute small help text for its readable field error.

Not canonized or repaired in this documentation pass: no unresolved defect from the scored finish fixes. The very small diagram boundary annotations are diagram-local labels, not a reusable type role. The finish verdict covers the scored fixes and sampled captures; it does not establish an exhaustive audit of every surface or a completed experiment campaign. The subsequent criteria-input review independently cleared its three scoped fixes: preserved invalid edits and validity, readable field errors and mobile input sizing. This documentation update follows the current source, `artifacts/verification/criteria-input/reviewer-recheck.json` and its saved mobile capture; it does not rerun the interface or evaluation.
