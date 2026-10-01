# Acceptance and meaningful regression tests

Implement these as automated tests or explicitly recorded acceptance checks; this file is not proof they have passed. Small hand-calculated fixtures are appropriate for unit correctness. End-to-end statistical claims must use the actual model-agent workflow.

## Numeric/data contract

| Test | Expected evidence |
|---|---|
| Odd/even and half-cent medians | Exact Fraction values; six-decimal half-even strings |
| Median of ratios vs ratio of medians | For($100,1sqft),($200,4sqft), ppsf median75, not60 |
| Empty selected month | Count0, null medians; positive→0 count MoM=-100;0→positive and0→0 null |
| Missing vs empty partition | Manifest incomplete is error; complete no-match month is valid |
| Filter endpoints | Price equal lower/upper included; raw cents unaffected by display |
| Identity | duplicate record_id fails ingestion; repeated listing_id with fresh records counts twice |
| Month arithmetic | December→January and leap-year timestamps; previous12 calendar months, not365days |
| Overlap MoM | First row of shifted window uses predecessor outside visible window |
| Percent semantics | First-to-last12 rows is11intervals; true YoY uses m-12 |
| Units/rounding | Exact0.09290304 conversion and half-even display; no numeric re-aggregation in UI |
| Ranking | Pooled per-record ppsf; exact tie then ZIP; no-data rank null; no averaging monthly medians |
| Data regeneration |34,560 rows,24 complete months, stable CSV byte SHA across two runs |
| Partition paths | Indexed/fullCSV yield equal record-ID multisets and numeric receipts on clean data |

## Workflow and framework

- Probe exact Fast Agent version/import/config/lifecycle/named role call; fresh source/follow-up histories.
- A no-feedback clean query reaches completed output with required Price/Supply receipts.
- Live index-omission fixture causes reviewer REFINE, planner `full_csv`, Region activation and rerun. Assert actual downstream output changes upstream executed strategy and active-agent set; immutable query hash stays equal.
- Exact rescan with genuinely sparse complete data produces `limited`, with no changed filter or invented rows.
- Persistent inconsistent receipts fail. Repeated identical plan, third refinement, forbidden price-band widening and unsupported composer fact are rejected.
- All six role definitions are distinct; Region is conditional rather than always hidden/off. Trace shows role decision→validated intent→tool receipt→aggregate.
- Malformed model output gets at most1 recorded repair; subsequent failure is output-contract violation in an eligible harness case. Transport retry is separate and cannot change seed.
- Controller/API/harness call the same `run_analysis`; no evaluator-only bypass to pure math.

## MR validity and sensitivity

For each MR: deterministic transform hash, valid input and precondition proof, nonidentity/effect witness, null handling, exact compared paths, expected tolerance. Include at least one deliberately invalid case (wrong subdomain) that must be labeled invalid, not pass. Invariance cases must compare nonnull data.

Build a small explicit mutation/control table:

| Deliberate fault | Expected detector | Suitable scope |
|---|---|---|
| Use first record as median | MR01 | Tool+MR integration under policy simulation; additional live capture if testing full MAS |
| Deduplicate by listing_id | MR03 | Numeric tool and actual comparator control |
| Reverse sqft→sqm conversion | MR04 | Presentation unit integration and frontend formatting |
| Keep source price band while scaling | MR08 | Transform preflight invalidates or count/membership checks fail; distinguish invalid harness control from application violation |
| Broaden band cached with old query key | MR05 | Workflow/tool selection cache integration |
| Reuse all-region count for subset | MR06 | Tool+comparator integration |
| Set first-row MoM null unconditionally | MR07 | Comparison-month integration |
| Add USD as cents | MR09 | Transform-unit regression and median-shift relation |
| Aggregate before ZIP filtering | MR10 | Tool+comparator integration |

A mutation control is counted as killed only if the intended assertion reports the expected mismatch; a crashed tool or REPLAY_MISS is not a kill of the numerical MR. Controls are **excluded** from natural headline violations. Labels and campaign IDs must make this explicit. Do not weaken strict replay keys to accommodate unseen mutant decision contexts.

## Harness/statistical integrity

- Exactly30 distinct eligible base hashes per required MR at freeze, all 3 source/follow-up seed pairs present; changing seed/display does not increase base count.
- Source/follow-up pairing and content hash verified; overlapping windows aligned by month key.
- Duplicate/missing case keys cause summary failure, not double counting or silent omission.
- Base any-seed aggregation tested against fixture outcomes; e.g.1violation among3 seeds for one base yields one violating base, not1/90 headline.
- Wilson checks0/30,15/30,30/30; n=0 has no rate/CI; bounds stay[0,1]. No Wald zero-width interval.
- Invalid and execution-error outcomes excluded appropriately but block minimum/completeness when unresolved; eligible agent-output failures remain violations.
- Top3 ordering is deterministic from actual rates; fewer than 3 positive rows yields truthful fallback wording.
- Contract/MR changes invalidate campaign/capture hashes; previous evidence retained.

## Replay, UI and final package

- Replay exact-match decision corpus only; changed request/schema/tool receipt/seed/prompt fails visibly. No fuzzy lookup, network fallback, final-output loading or cached headline copy.
- Run offline with external sockets disabled; Fast Agent playback roles invoked and actual Python tools called. Compare recomputed headline to live/capture-derived reference, ignoring only timestamps/mode/run IDs.
- Browser smoke test: filter→run→12 months table/chart→trace→export→results drilldown. Units toggle updates display without canonical-query mutation. Empty/null/error/synthetic/mode states are obvious.
- Frontend build/type checks, API contract/error checks, path validation and local-only settings.
- Final report10-12 pages, rendered and visually inspected; all figures/tables sourced from saved evidence. Required repo files present; clean-checkout commands actually exercised.

`make submission-check` should implement structural coverage assertions and link/hash/page-count validation, not assert subjective claims such as “nice UI” without screenshots/user-flow evidence. Save machine-check output and a short manual acceptance record. Do not mark this handoff checklist completed merely because it has been copied into the repository.
