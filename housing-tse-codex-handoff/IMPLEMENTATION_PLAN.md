# Implementation plan with dependency gates

This is the complete build, not the earlier architecture-only submission. Prioritize a verified core and honest experiment over optional features. Time estimates are intentionally omitted until the framework/model pilot measures local throughput. The deadline printed in the assignment is16 October 2026; no remaining time budget is assumed.

## P0 - Requirements and framework proof

Tasks: inspect original PDF and diagrams; copy/reconcile root AGENTS; record defaults; initialize Python/frontend projects and locks; run the Fast Agent probe, one local seeded JSON decision and strict playback; define shared contracts from supplied schemas; add a tiny exact arithmetic test module. Confirm Python 3.12 compatibility and the actually resolvable package version. Save official-source URLs and actual installed signatures.

Gate: imported/registered named Fast Agent roles execute against chosen model; JSON parse/policy rejection and one live→playback decision work; effective seed profile/digest recorded. If local inference is blocked, continue deterministic data/contracts/UI but mark empirical/live gates incomplete. Do not claim a deterministic test double satisfies this gate.

## P1 - Frozen data and numeric kernel (depends P0 contracts)

Tasks: implement generator/config, exact rounding, CSV loader/quarantine, manifest/hash, immutable query normalization, partition index/full scan, monthly price/count tools, lookback and ranking semantics. Build independent tiny preflight selector for membership/witnesses. Add fixtures for duplicate record IDs, repeated listing IDs, missing partitions, empty/zero months, UTC boundary and inclusive price endpoints.

Gate: generator yields34,560 valid records across24 months; regeneration byte hash equals committed snapshot; default12-month plus YoY works; unit fixtures match exact values; indexed/full-scan select equal multisets. Commit CSV and manifest, not just generator.

## P2 - Actual MAS and bounded feedback (depends P0+P1)

Tasks: six prompts, strict decision adapters, intent dispatcher, controller, tool receipts, aggregator, fact registry/composer, JSONL trace, typed errors and budgets. Use model choices for planning/review/action, deterministic arithmetic in tools. Trigger sparse or omitted-index fixture; capture actual live reviewer/planner decisions.

Gate: no-loop path and real feedback path both execute; back edge revises strategy and active agents, old receipts invalidated, query hash immutable; max refinements/invalid actions stop correctly. Trace links from decision to tool receipt to aggregate. Composer has no unsupported number generation.

## P3 - First MR and strict reproduction spine (depends P2)

Tasks: implement MR01 source→transform→reexecute→compare, case statuses, seed lineage, capture keys and replay. Test3 bases*3 seed pairs as pilot; measure role calls/tokens/duration. Make an offline replay of those exact cases, rerunning tools and comparisons, and verify that a changed prompt/receipt fails. Use fresh role contexts.

Gate: pilot actually runs end to end using the production workflow; transformed input traverses ingestion; no final-output cache; live and replay canonical results/summary match, traces say which mode ran. Keep pilot separate from frozen headline campaign.

## P4 - Complete MR suite and statistics (depends P3)

Tasks: implement remaining9 MRs, per-MR preconditions/effect witnesses, manifest-driven transformations, typed result records, grouped base summaries and Wilson intervals. Validate all 30 candidate bases independently for every MR and replenish deterministically when necessary. Freeze final eligible cohort and experiment manifest. Implement reporting for invalid/contract/infrastructure statuses. Add comparator mutation controls and known CI anchors.

Gate: ten catalog implementations match the formal definitions;30 distinct eligible bases/MR;3 recorded seed pairs; all families present; denominator and transformation lineage checked; synthetic/injected controls excluded from headline cohort. Full suite expected900 comparisons,1800 logical legs before source reuse.

## P5 - Backend and interactive UI (core can overlap P3/P4 once P2 service stable)

Tasks: FastAPI job endpoints, local metadata store, generated TS types, Explore criteria/charts/table, Workflow graph/event drilldown, Results evidence drilldown, Data/provenance view and CSV/JSON exports. Mode/synthetic badges and empty/error/null states. White background, subtle filled technical boxes, accessible keyboard use and mobile layout.

Gate: user can choose filters, run actual workflow, inspect12-month chart/table, see feedback evidence and export; API and harness use the same service. Browser smoke test and screenshots; no mocked chart data presented as actual results.

## P6 - Headline execution, reproduction and diagnosis (depends P4; UI not a prerequisite for model batch)

Tasks: execute frozen live campaign with budget monitoring; preserve failures; resolve infrastructure without selective case removal; generate headline from raw cases; reproduce offline; rank actual violated MRs; build minimal evidence-backed RCA for top 3, recording pre/post-fix campaigns. If zero/fewer failures, write honest limited findings and separate controls.

Gate:≥30 completed eligible bases per MR and3 paired outcomes/base; actual raw900 comparisons; rate/CI tables regenerate; zero unresolved execution errors for official-complete rows; live loop trace; hashes and strict replay corpus shipped. CIs discussed at actual width, no overclaim of independence or market correctness.

## P7 - Report and clean submission (depends P5+P6)

Tasks: update three architecture pages; render final10-12-page report from real data; include system/source/contract/MRs/results+CIs/top 3RCA/threats/half-page reflection; complete NOTEBOOK/AI_USE; finalize README, locks, scripts and evidence index; test clean-checkout setup then disconnected reproduce; inspect report page images and screenshots.

Gate: assignment requirement matrix has a verified evidence path for each row; no placeholder numbers, false live claims or broken links; all commands actually executed; PDF page count10-12; repository frozen snapshot and seed/model/capture provenance present. `make submission-check` returns success only when complete, otherwise reports specific missing evidence.

## Two-person ownership without integration drift

Suggested split: PersonA owns contracts/data/tools/framework/controller; PersonB owns harness/statistics/frontend/report assembly. Agree contracts, statuses and trace schema together first. PersonB can build UI against schema-valid **labeled** fixtures while A completes service; replace them before UI acceptance. One person audits the other's MRs with counterexamples. Both review headline/RCA and AI disclosure. Keep each milestone mergeable and avoid parallel edits to shared schemas without explicit coordination. This is a team work allocation, not an instruction to create subagents automatically.

## Priority cuts if time is tight

Keep: all assignment requirements, actual MAS loop, ten rigorous MRs/three families,30 bases+seeds, exact data/metrics, meaningful UI, full evidence and reproduction. Defer: free-text input, public deployment, authentication, alternative cities/providers, native MCP server migration, animation, live listings and advanced caching. If a mandatory gate remains unmet, report it as incomplete rather than dilute semantics or fabricate evidence.
