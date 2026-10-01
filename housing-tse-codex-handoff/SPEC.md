# Implementation specification v1.0

## 1. Objective and authority

Build a small, interactive, reproducible application in which cooperating Fast Agent specialists scan monthly residential listing observations and produce a precise twelve-month trend. Evaluate ten metamorphic relations end to end; publish measured violation rates, 95% intervals and evidence-based diagnosis. This is a build specification, not an implementation or an experimental finding.

Assignment citations refer to `sources/originals/Assignment_MR_Housing_final_v2.pdf`: p.1 §1 defines the application, frozen snapshot, feedback, conditional iteration and action-changing dependency; p.1 §2 requires an output contract before MRs and at least eight relations across three families; pp.1-2 require 30 distinct bases per MR, three fixed seeds for nondeterminism and CIs; p.2 §§2-4 defines diagnosis, repository, report and disclosure; p.3 allows generated data; p.4 explicitly allows documented assumptions. See `sources/REQUIREMENTS_MATRIX.md` for all mappings.

## 2. Fixed defaults

- Geography: Dallas-themed synthetic listing feed, twelve explicitly enumerated ZIP codes. It is a software test dataset, not an estimate of Dallas market prices or representative metro coverage.
- Snapshot: monthly observations from **2024-10 through 2026-09 inclusive**, 24 months. Default visible window: **2025-10 through 2026-09**, twelve completed UTC calendar months. Never use today's date at runtime to slide the frozen experiment.
- Language/runtime: Python 3.12; Fast Agent (`fast-agent-mcp`); FastAPI; Pydantic v2; exact arithmetic in Python. SQLite/CSV for the snapshot and run index. No vector store, scraping, external listings API, cloud queue or database service is needed.
- UI: React + Vite + TypeScript; a maintained chart library chosen and locked at implementation. A few clean pages, white background, lightly filled boxes, short technical labels. Build a working accessible UI before decorative work.
- Model: local Ollama running `qwen2.5:7b-instruct` as a pragmatic initial candidate, subject to the mandatory capability probe. Freeze actual model digest, quantization, Ollama version, prompt hashes and Fast Agent lock. Use three derived model names carrying fixed seed defaults. No universal framework `seed=` API is assumed.
- Ten required MRs (`MR01`-`MR10`), three paired seeds, 30 valid distinct bases for each. Extra cases are allowed only with versioned manifests and consistent denominators.
- Concurrency: one analysis at a time initially; independent specialist agents may run concurrently in isolated contexts. Finish correctness before increasing throughput.

## 3. Scope and exclusions

Include deterministic dataset generation, frozen CSV, strict ingestion, typed Python tools, six real model-agent roles, bounded feedback, charts and tables, trace viewer, harness, offline replay, report sources, final PDF, NOTEBOOK.md and AI_USE.md. Queries are structured form criteria. Free-text parsing is optional after the mandatory work; it must end in user-visible structured criteria before execution.

Do not substitute aggregate price indices for per-listing scans. Do not describe a sale-date or previous-sale field as a monthly active-listing snapshot. Do not use a single-date file relabeled into twelve months as observed data. Generated prices are explicitly synthetic. No forecasting, investment recommendation, causal market explanation, user authentication or public deployment is required.

## 4. Output contract: define this before implementing MRs

### 4.1 Request

`schemas/analysis_request.schema.json` is authoritative syntax. Required keys: `dataset_id`, `window_end`, `criteria`, `display`, `compare_regions`, `seed`. `window_end` is YYYY-MM; start is exactly end minus eleven calendar months. Criteria contain nonempty ZIP and property-type sets, inclusive bedroom range, inclusive integer-cent price band, inclusive integer sqft band. Null lower/upper limits mean unbounded, not zero. Normalize set order and duplicates, preserve ZIP strings, reject unknown values, lower>upper, noninteger money and invalid date. Default full criterion: all allowed ZIPs/types; bedrooms 1-5; no price or sqft band. Unknown fields fail validation.

`seed` is experiment metadata and runtime model selection, not a housing filter. `display.money` is `USD` or `USD_THOUSANDS`; `display.area` is `SQFT` or `SQM`. Currency identity remains USD. No foreign-exchange rates enter this assignment. `compare_regions` requests ZIP-level output; region diagnostics may still run internally on feedback without changing this public flag.

### 4.2 Numeric result

`schemas/analysis_output.schema.json` defines the public result envelope. Stable statistical fields live under `canonical`. Metadata, narrative, warnings and trace identifiers are outside it.

For each requested calendar month m, always emit exactly one row, sorted oldest first:

| Field | Definition |
|---|---|
| `month` | YYYY-MM |
| `listing_count` | Number of qualifying valid observation records in m, including distinct records with equal listing IDs |
| `median_price_usd` | Median of qualifying integer-cent prices divided by 100 |
| `median_ppsf_usd` | Median of the individual exact ratios `(price_cents/100)/sqft`; never ratio of medians |
| `price_mom_pct` / `ppsf_mom_pct` | 100*(x_m/x_(m-1)-1), same filters; null if prior month unavailable or either median null |
| `price_yoy_pct` / `ppsf_yoy_pct` | 100*(x_m/x_(m-12)-1), same filters; null under the same conditions |
| `count_mom_pct` | 100*(n_m/n_(m-1)-1); null if predecessor unavailable or zero |

A present complete month with zero matches has count 0 and null medians. Null is not 0. Count change from positive to zero is -100%; from zero to positive is undefined/null; 0 to 0 is null. No pseudocount, infinity, NaN or epsilon denominator. For medians, empty means null; odd is the middle sorted value; even is the exact arithmetic mean of the two central values. Never interpolate a quantile by library default.

Summary:
- `window_price_change_pct` / `window_ppsf_change_pct`: last visible median versus first visible median. Twelve monthly observations span **eleven** monthly intervals; label as first-to-last change.
- `last_month_price_yoy_pct` / `last_month_ppsf_yoy_pct`: equal the last row's year-over-year values, a true twelve-month interval when lookback exists.
- `total_observations`: sum of the twelve monthly counts; not unique properties and not a single-month inventory.
- `zip_rankings`: if `compare_regions=true`, each ZIP's pooled median individual ppsf over the twelve visible months, sorted descending by exact median, then ZIP ascending; no-data ZIPs have null median and null rank and sort last. Ranks are ordinal 1..n among nonempty ZIPs. When false return an empty list. Do not average monthly medians.

The same filter applies to all visible and comparison months. Build the union of visible months, their m-1 and m-12 lookbacks before scanning; never filter to the visible window and then attempt YoY. Unavailable lookback months produce null deltas, not an ingestion error. Public regional rows are requested ZIPs only. Region diagnostics used to inspect sparsity never alter the global statistical result.

### 4.3 Arithmetic and display

Keep input prices as positive integer cents and sqft as positive integers. Use `fractions.Fraction` (or equivalently proven exact rational arithmetic) through ratios, medians and percentages. Sort on exact values. Serialize monetary/ratio/percentage values as decimal **strings with six digits after the decimal point**, round half-even exactly once at serialization; normalize negative zero. Counts remain integers. Frontend must not recompute medians or percentages.

Display conversion is downstream: USD_THOUSANDS divides USD values by 1000; SQM uses exactly 1 sqft = 0.09290304 sqm. Price per sqm equals price per sqft divided by 0.09290304. Format visible USD to 2 decimals, thousands to 3, ppsf/ppsqm to 2 and percentages to 2; tooltips can show canonical six-decimal values. These are formatting choices only. The output also includes `presentation={money,area,monthly:[{month,median_price,median_price_per_area}]}` with six-decimal strings derived from the serialized canonical values using the same exact conversion factors; it is a display projection, never a source for statistics. Raw JSON/CSV export preserves canonical strings and units. Frontend decimal-to-number conversion is for chart coordinates only, never MR checks.

### 4.4 Ingest and identity

See DATA_CONTRACT. The row grain is an active listing observation at a monthly snapshot, not a sold property. `record_id` uniquely identifies an observation; `listing_id` is a nominal label and may repeat across months or repeated observations. Duplicate `record_id` is an invalid dataset and stops ingestion. Distinct `record_id` with equal business fields is counted as a separate observation. The replication MR creates fresh record IDs and intentionally retains listing IDs. This contract matches the assignment's doubling-count example; adding unique-property metrics later requires separate MRs.

Malformed rows (bad ZIP/type, nonpositive price/sqft, out-of-domain bedrooms or invalid month) are quarantined with reasons before filtering. Never repair negative prices, infer months from sale dates, impute medians, drop low-count months or remove outliers from headline data. Manifest missing/incomplete partition is `DATA_INCOMPLETE`, not a zero count. Errors are structured, not empty successful results.

### 4.5 Stable versus variable output

`canonical` is the MR comparison surface, projected per MR. Agents may choose different diagnostics, bounded routes and wording. Do not compare full JSON bytes or free text. Metadata must identify snapshot byte hash, logical multiset hash, query hash, output contract version, model profile, requested/effective seeds, run mode, prompt bundle hash and trace path. `quality.status` is `complete` or `limited`; limited means truthful low-support statistics, not failure. A contract-valid low-count median remains part of the canonical result. Agent parse/policy failures do not get silently repaired by a hidden deterministic answer.

## 5. Multi-agent architecture and actual executable decisions

The later delivered no-fills diagram is the structural baseline: one Orchestrator owns planning; Price, Supply and Region Specialists return to it; deterministic Trend Aggregator; Coverage Reviewer; Report Composer. The earlier file separates Criteria Interpreter. We preserve the later merge. Reintroducing a small planner module does not create an extra advertised agent. See ARCHITECTURE for graph and transition table.

Six role agents must be invoked through Fast Agent in live mode, with distinct frozen instructions and typed outputs:

| Role | Input | Executable output | Allowed project tool intents |
|---|---|---|---|
| Orchestrator/planner | normalized query, capabilities, previous plan, reviewer feedback | `PlanDecision`: scan strategy, active specialists, diagnostics | `plan_scan`, `inspect_manifest` |
| Price | plan + immutable selection handle | `SpecialistDecision`: full price aggregation request, partition order | `price_stats` |
| Supply | plan + selection handle | `SpecialistDecision`: count and availability request | `supply_stats` |
| Region | plan + requested ZIP list/diagnostic purpose | `SpecialistDecision`: pooled ranks or coverage matrix | `region_stats` |
| Coverage Reviewer | aggregate, manifest/selection completeness, previous attempts | `ReviewDecision`: `ACCEPT`, `REFINE`, `ACCEPT_LIMITED` or `FAIL` with signal and upstream action | `coverage_diagnostics` |
| Report Composer | final canonical contract + quality flags | `ReportDecision`: ordered fact IDs and caveat codes | `render_fact_summary` |

These are **project-owned types and tool capabilities**, not alleged Fast Agent classes. For a small local model, use a two-phase JSON-intent protocol: Fast Agent emits a strict decision; a Python dispatcher validates it and runs the named typed tool. No arithmetic is performed by the LLM. No shell/filesystem/web tools are exposed. Log `decision_mode=intent_dispatch`; do not claim the framework emitted native MCP calls. Native tool integration is optional after parity tests.

Price/Supply are mandatory. Region runs if public comparison is requested OR the reviewer requests geographic coverage diagnosis. A specialist chooses a scan execution order but cannot omit requested partitions, alter filters, select a different median definition or truncate records. Every numeric result must contain tool receipt IDs for the exact dataset and selection. The aggregator merges verified receipts and checks partition/selection equality; an indexed-pass completeness discrepancy is retained in a provisional aggregate for Reviewer, whereas an incomplete raw snapshot is immediately DATA_INCOMPLETE. Only complete authoritative results can become final output; it must not independently synthesize all results while ignoring specialist decisions. The composer selects grounded fact IDs; Python renders numbers from final facts and discards unsupported claims with a recorded error. This creates auditable responsibilities without delegating numerical correctness to prose.

## 6. Bounded feedback that changes upstream action

Initial plan: `scan_strategy=indexed`, Price+Supply, Region only when requested. The indexed route is an exact scan through a prebuilt partition index, not a statistical sample. Supply reports completeness and counts.

Downstream review signals:
- `INDEX_COVERAGE_MISMATCH`: required manifest partition absent from the index/receipts though present in CSV.
- `SPARSE_SLICE`: any visible month count <5 after an indexed complete scan. The threshold is a support rule, not a confidence interval and not an MR precondition.
- `RECEIPT_MISMATCH`: specialists refer to different selection hashes or disagree on row coverage.

For first-pass mismatch/sparsity, reviewer emits `REFINE` with action `EXACT_RESCAN_WITH_REGION`. Planner must switch to `scan_strategy=full_csv`, force Region diagnostic, clear selection-dependent receipts and rerun Price+Supply+Region. This changes both the scanning algorithm and the active agent set. It does not change criteria, visible window or statistic definitions. Trace records plan diff and a changed execution path. After an authoritative complete rescan, sparse results can be accepted as `limited`; genuine absence cannot be cured by inventing observations. Persistent receipt mismatch is a failure, not a quality caveat.

Maximum **two refinements after initial pass** (iterations 0,1,2). No repeated identical plan hash. After a second scan, a further refinement is permitted only for a new resolvable receipt signal with action `REBUILD_INDEX_AND_RESCAN`; otherwise stop `ACCEPT_LIMITED` for real sparsity or fail integrity errors. A deterministic controller enforces budgets and immutable query; the Reviewer still makes and records the conditional decision. Wrong or forbidden decisions fail with `AGENT_POLICY_ERROR`, not a substituted decision. Schema repair is at most one explicit extra model call, with its own trace and fixed seed. Infrastructure retries are separate and do not consume semantic refinements.

Required execution evidence: one natural low-support frozen fixture OR an explicitly injected index omission must cause a **live Fast Agent** reviewer REFINE, revised planner decision, changed tool path and rerun. Test should assert both action/agent-set changes. Copy its actual JSONL excerpt and graph cycle to the report. A scripted example trace in this bundle is illustrative only. Injected controls remain out of the headline evaluation.

## 7. Service contract

Implement `/api/v1`; export generated OpenAPI and generated TypeScript types. No arbitrary file path or SQL in requests.

| Method/path | Behavior |
|---|---|
| GET `/health` | versions, model/replay availability; no secrets |
| GET `/datasets` | frozen dataset IDs, source kind, month range, ZIP/type enums, provenance link, hashes |
| GET `/datasets/{id}/quality` | per-month valid/quarantined counts and manifest completeness |
| POST `/analyses` | validate request; return 202 `{run_id,status_url}`; save immutable request and schedule workflow |
| GET `/analyses/{run_id}` | 200 pending state or completed envelope; failed state includes typed error |
| GET `/analyses/{run_id}/trace` | ordered JSON events, cursor pagination, including feedback and tool receipts |
| GET `/analyses/{run_id}/export?format=json|csv` | canonical numbers; CSV one row per month with units in headers |
| GET `/evaluations` | previously executed evaluation manifests, status, mode, completeness |
| GET `/evaluations/{id}` | summary rows, denominators, intervals, invalid/error counts, linked evidence |
| GET `/evaluations/{id}/cases/{case_id}` | source/follow-up requests, outputs, transform witness, field differences, seed/trace paths |

Evaluation runs are CLI initiated; UI reads committed local results. A UI launch button is optional and must create a visible background job with a budget, never run on ordinary page navigation. Poll analysis status initially; SSE is optional. API 422 invalid request; 404 unknown IDs; 409 stale snapshot/replay miss; 503 unavailable model; unexpected server errors get stable error IDs. Job failure status contains code, safe message, stage and evidence path. Use `DATA_INVALID`, `DATA_INCOMPLETE`, `AGENT_OUTPUT_INVALID`, `AGENT_POLICY_ERROR`, `BUDGET_EXCEEDED`, `REPLAY_MISS`, `TOOL_ERROR` consistently. No HTTP success masquerading as a numeric zero result.

Use SQLite plus a bounded local worker for run metadata and JSON artifacts on disk. Immutable per-run directory, atomic final writes, no process-global mutable conversation or mutable dataset. Capture logs without private credentials. Browser can only request declared dataset IDs and run IDs.

## 8. UI acceptance

### Explore

Dataset badge explicitly says Synthetic Dallas test feed; month-end selector; ZIP multiselect; property types; bedroom bounds; USD price and sqft bounds; display toggles; region comparison toggle; Run button. Show normalized visible dates before running. Seed and execution mode can sit in an expandable reproducibility panel. Reject an empty ZIP set, inverted bands and out-of-coverage windows in both UI and server.

Results: median list price line, median individual ppsf line, listing-count bars, first-to-last and last-month YoY cards with precise labels, twelve-row accessible table, regional table/ranking when requested. Tooltip shows month, value/unit and count. Gaps are null, never connect across missing values without an explicit visual indication. Distinguish no matches, unavailable source partition, running, limited support and failed model. Filtering changes require rerun; display-only changes must not trigger a new dataset query. Exports include seed and dataset hashes.

### Workflow

Plain graph of Orchestrator, specialists, aggregation, review, compose. Mark the feedback edge and highlight actual iteration numbers. Adjacent event list shows strategy, active agents, signal, plan diff and tool receipts; click an event for input/output JSON. Show mode LIVE / REPLAY / POLICY_SIMULATION clearly, and show injected fixtures as such.

### MR results

Table with MR family, distinct bases attempted/eligible/completed, seed list, violating bases, base-level rate and 95% Wilson interval, seed-pair rate, invalid/error counts, completeness badge. Drill down source/follow-up with changed criteria/data field and exact compared values. Charts supplement, never replace the table. Display a provenance banner for replay: decisions recorded from a named live campaign, numeric tools and comparisons re-executed now.

### Data/provenance

Month coverage chart, row schema, generation recipe/hash, frozen CSV hash, limitations, quarantine reasons, library/model versions. Do not label synthetic counts as measured Dallas inventory. White page, dark text, lightly filled cards, clear focus indicators and accessible contrast. Keyboard controls and readable empty states. Desktop and 390px viewport must work; provide screenshots and one browser smoke test of run → chart/table → trace → export.

## 9. Evaluation and reproduction

MR_CATALOG and EVALUATION_PROTOCOL are normative. Compare canonical outputs from the actual same workflow used by the UI/CLI, not a parallel evaluator-only implementation. Numeric tool unit tests can use hand-computed oracles; main MR evaluation uses source/follow-up relations. Each leg starts with fresh agent contexts and immutable transformed input. All transformations cover lookback months when relevant. Source result caching may share an identical source among MRs only if the full input/profile/seed/content hashes match; keep logical-case lineage.

Budget for ten MRs *30 bases *3 paired seeds =900 source/follow-up comparisons, at most1800 analysis executions without source reuse. At five mandatory role calls per no-region no-loop analysis that is at least 9000 model decisions before repair/feedback; measure pilot cost, do not promise a fabricated runtime. Start with one MR/3 bases/3 seeds, then a complete MR, then the full campaign. Optional source reuse and deterministic numeric caches must not replace follow-up execution or hide agent invocations.

Live mode calls Fast Agent+local model. Replay mode executes Fast Agent's documented playback model for strict matched captured decisions, then reruns project tools, aggregation, control flow and MR checks. Policy simulation is a third, explicitly auxiliary mode; it cannot establish empirical live MAS results. Missing live corpus blocks an honest replay deliverable, and must be reported instead of generated fake cassettes. See FAST_AGENT_INTEGRATION for replay invariants.

`make reproduce` must verify hashes, disable external network/model access, read frozen data and manifests, rerun 900 comparisons, regenerate raw results + summary + CIs, verify counts and emit a comparison against the saved headline table. It may neither load saved final canonical outputs as its execution path nor merely copy a precomputed CSV. Repeated replay is reproducibility evidence, not extra statistical samples. Live/captured campaign and replay summary are separate artifacts with common lineage.

## 10. Repository layout and completion

Create `src/housing/{contracts,data,tools,agents,workflow,api,evaluation,replay,cli}`, `frontend/`, `tests/{unit,integration,e2e}`, `data/{frozen,manifests}`, `configs/`, `prompts/`, `artifacts/{evaluations,traces,cassettes,rca,figures}`, `report/`, Makefile, Python/frontend lockfiles, NOTEBOOK.md, AI_USE.md and README.md. Keep handoff docs under `handoff/` if useful. Hash all evidence, use relative artifact paths in committed manifests, and exclude secrets/venvs/caches.

Completion requires every gate in IMPLEMENTATION_PLAN and TEST_ACCEPTANCE, at least 30 completed eligible bases per MR with all seeds, actual live loop trace, reproduced headline table, truthful top-three RCA (including zero-failure case), final10-12-page PDF and clean checkout reproduction instructions. A pretty UI, eight MR descriptions or a deterministic-only toy does not complete the assignment. No claim in the report may imply execution that did not occur.


### Prompt envelope and trace payload binding

Each semantic role prompt contains role/version, state iteration, canonical housing query, dataset-view identity, allowed action schema, previous plan/review action if applicable, and the minimum relevant evidence (counts, partition completeness and receipt hashes; not raw listing dumps). The controller binds trusted data/selection arguments after a decision. Volatile run IDs, timestamps and machine paths stay outside prompt bytes. Limit prompt length against the frozen model context; overflow is an explicit error, never silent truncation. Configure8192 context tokens and1024 maximum generated tokens initially, verify provider settings in the probe, and adjust with a version bump if needed. Trace envelopes use schemas/trace_event.schema.json; per-event payload requirements are in templates/trace_payload_contract.json.


See [REPRODUCIBILITY_CONTRACT.md](REPRODUCIBILITY_CONTRACT.md) for exact hash projections, volatile-field exclusions and the offline command acceptance protocol. Upstream **semantic** tool-receipt hashes exclude run IDs, durations, paths and trace sequence references; full byte hashes remain separate integrity evidence.
