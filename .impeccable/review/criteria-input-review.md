disposition: ship

Current disposition covers only the three scoped criteria-input findings. The initial review below is preserved as a pre-fix record with disposition `fix`; the completed recheck follows it.

## persistence

Focused review of the numeric criteria correction only. The earlier finish review and three-item finish verdict remain unchanged. Read the changed input parser, CriteriaForm, App integration, CSS, three Node tests, and saved evidence under artifacts/verification/criteria-input/. Opened the saved desktop and mobile field captures. No browser interaction, live/replay job, detector, aesthetic-direction review or test execution was performed by this reviewer.

## fidelity

| Concern | Verdict | Evidence |
|---|---|---|
| Exact USD conversion | pass | Decimal text is converted through BigInt cents before conversion to a safe JSON integer. `250000.25` becomes `25000025`; there is no float multiplication or truncation. |
| Integer boundaries | pass | The largest safe cent integer is accepted exactly; one cent above it is rejected. Area accepts positive whole numbers only and checks its BigInt value before Number conversion. USD zero and blank unbounded values are handled intentionally. |
| Invalid input | pass within a mounted form | Invalid raw text remains visible; custom validity blocks native form submission; aria-invalid and an associated error identify the field. The saved blocked-submit record reports zero new jobs for fractional area and excessive USD precision. |
| Explicit restoration | pass | Form revision keys reset uncontrolled values and error state on recorded-criteria restore, capture selection and recent-run restoration. The restore control has type="button", so an invalid field does not block restoration. |
| Ordinary view changes | fail | `expanded && <form>` unmounts BoundInput when “Your slice” closes, and `page === 'explore'` unmounts CriteriaForm on tab navigation. Raw text and error state are local; invalid edits therefore disappear and reopen as the last valid canonical value without an explicit restore. |
| Error accessibility | partial | Errors have descriptive text, associated ARIA metadata, a visible error border and a contrasting danger color. The measured 13.125px error font is below the supplied 14px secondary-text floor. |
| Mobile input sizing | fail | The new text inputs inherit `.field { font-size: 0.8rem }` through `input { font: inherit }`: 12px at the 15px root, with no mobile override. They need an explicit 16px mobile font minimum to avoid iOS Safari focus zoom. The loaded craft-floor.md does not itself state numerical 14px/16px minima; the error minimum came from the scoped review request, and the input minimum is this review's mobile usability finding. |
| Coverage limits | recorded | The three parser tests cover the numerical regression and representative boundaries. They do not establish raw/error-state persistence across collapse or navigation. The root agent's actual exact-cent API submission check was still in progress when this review was requested. |

## ceiling

Not reopened: this review concerns functional exactness, state preservation and error readability only.

## material_fixes

1. Preserve raw numeric text and its validation state across criteria collapse/reopen and ordinary tab navigation; reset it only for explicit restore/capture/run-load actions. Ensure custom validity is restored if inputs remount. Verify that invalid text remains visible and still prevents job creation after both navigation paths.
2. Raise `.field .error-text` from `0.875rem` at the 15px root to at least 14px; verify the computed size and wrapping on the existing desktop/mobile error states.
3. Give the new USD/area text inputs an explicit mobile font size of at least 16px; verify the computed size and that long valid/invalid text remains editable within the existing two-column form.

## keep

Keep decimal-text/BigInt parsing, safe-integer guards, invalid-text visibility, native submission blocking, associated field errors and explicit restoration keys.

## scoped recheck verdict

1. **Resolved — raw text and validity persistence:** In a separate browser tab, invalid USD `250000.255` and area `1400.5` survived criteria collapse/reopen and Workflow/Explore navigation on desktop and 390px mobile. Each field retained its raw text, custom validation message and invalid state. The hidden form and hidden Explore subtree computed `display: none`. Real invalid form submissions on both viewports remained blocked; the before/after local API job IDs were identical, with zero new jobs.
2. **Resolved — error readability:** Both error messages computed 14px on desktop and mobile. Fresh captures show readable wrapping inside the two-column form without horizontal text overflow.
3. **Resolved — mobile input sizing:** All four new bound inputs computed 16px at 390×844. Invalid values remained editable, and document width stayed 390px.

Fresh actual JPEGs: `artifacts/verification/criteria-input/reviewer-desktop.jpg` (1512px desktop, full page) and `reviewer-mobile.jpg` (390×844, scoped input viewport). Both were opened during this recheck. Exact DOM measurements, preserved values/validity, API job IDs and timestamps are recorded in `reviewer-recheck.json` in the same directory. The temporary viewport override was reset to the normal 1512×805 viewport, and the reviewer's tab was closed.

The root agent's separate saved `restore.json` records explicit restoration of invalid `0.001` to a valid blank when the canonical value was already null. Its `exact-cent-submission.json` records API acceptance of typed USD `128655.25` as integer cents `12865525`; that auxiliary job was running at capture, and this review makes no claim that its analysis completed. This reviewer submitted no valid live or replay jobs.

Regressions from this scoped fix batch: none observed. No broader style review or detector was run. The earlier finish verdict remains unchanged.

## scoped remaining

clear. This ship covers the three scored criteria-input fixes, not the whole surface or the pending campaign.

disposition: ship
