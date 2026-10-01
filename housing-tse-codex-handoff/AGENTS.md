# Repository instructions for implementation agents

## Purpose and authority

Implement the TSE housing MAS assignment end to end from this handoff. The assignment PDF governs coursework requirements. SPEC governs application semantics; DATA_CONTRACT data/arithmetic; MR_CATALOG comparisons; EVALUATION_PROTOCOL statistical units. If these disagree, resolve and version the correction before evaluation. This document is intended to be copied to the future repository root; reconcile existing higher-priority repository instructions.

## Work style

Proceed with the documented defaults. Keep milestones small and reviewable; maintain NOTEBOOK.md as an execution record. No invented claims that a model, test, deployment or experiment ran. Ask only when blocked by a needed credential/model permission or genuine incompatible requirement; do not pause to approve ordinary reversible coding. No unsolicited external messages, paid services, scraping, deployment or personal listing data. Keep assignment deadline16 October 2026 and team size2 in documentation without inventing a submission hour.

## Structure and code

- Python 3.12, typed Pydantic v2 boundary models with extra fields forbidden. Use exact Fraction/integer arithmetic internally and six-decimal half-even serialization. No float filtering/statistics.
- Put domain contracts/tools outside API, frontend and agent adapters. One production `run_analysis` application service is used by API, CLI and harness.
- Fast Agent agents return role-specific validated decisions. Project dispatcher binds trusted tool arguments. LLM text never supplies statistical truth.
- Immutable dataset/request per run; no shared chat history. Do not change user criteria on refinement; change the scan strategy/diagnostics and specialist set.
- Small explicit state machine; no unnecessary framework mix, generic workflow engine or distributed services. Aggregator must consume specialist receipts, not bypass agent execution.
- Avoid guessed APIs. First run/preserve the framework probe and pin package/model versions. Never add a universal seed keyword without evidence it is supported and honored.
- Backend-generated schemas and TypeScript types must agree. No `any` for domain contracts; no frontend recomputation of canonical statistics.
- Store user-facing numbers/units and provenance clearly. Synthetic is an explicit label, not a footnote. No unsupported market or causal narrative.

## Evidence and experiment rules

- Preserve immutable raw campaign evidence, source/follow-up outputs, all seeds and failed attempts. Fixes produce new campaign/version identifiers.
- Ten MRs,≥30 distinct eligible completed bases each, all 3 fixed paired seeds. Invalid candidates and infrastructure errors remain visible. Do not remove inconvenient violations.
- Primary unit is a distinct base with any violation among the fixed seed panel. Wilson95% CI uses completed base count, not seed-run count. Explain dependent slices and limited generalization.
- Use exact/toleranced projections from MR_CATALOG; no arbitrary epsilon, float coercion or full-response equality. Require nonvacuity witnesses.
- Real live role calls and loop trace are mandatory. Policy-simulated fixtures and injected mutants are auxiliary only. Zero observed failures is a valid result with uncertainty.
- Replay matches exact semantic prompt/schema/tool/model/seed hashes, runs Fast Agent playback and recomputes tools/statistics/MRs. No saved final-output shortcut, fuzzy match or network fallback.
- NOTEBOOK.md records actual commands, timestamps, versions, outputs and interpretation; AI_USE.md records substantive AI work, mistakes and how caught, including this handoff.

## Commands to implement and keep working

`make setup`, `make data`, `make check`, `make dev`, `make evaluate-live`, `make reproduce`, `make report`, `make submission-check`.

`make check` includes Python lint/type/unit/integration checks and frontend type/build checks; browser smoke testing is appropriate after UI changes. Exact commands/versions live in the repository README/Makefile. Offline reproduction depends on completed setup and committed live capture. The final report PDF must be10-12 pages. Do not mark completion until clean-checkout evidence exists.

## Test priorities

Prioritize contract semantics, generator byte determinism, month/lookback boundaries, invalid/empty data, even medians, individual-ratio median, duplicate identity rules, price-filter inclusion, indexed/full-scan parity, actual loop changes, MR nonvacuity, paired lineage, Wilson anchors, replay misses and shared API/harness service. Use hand-calculated examples for unit tests; main empirical claims come from actual end-to-end runs. Add meaningful regression tests for discovered faults. Do not spend time on tautological tests that mirror a function's implementation.

## Security and packaging

Use local dataset IDs, parameterized access, whitelisted tool intents and relative evidence paths. Never accept arbitrary filesystem paths/SQL from the browser. No secrets in git, report, traces or cassettes. Commit locks, frozen snapshot, seeds, provenance, diagrams, compact evidence and reproduction instructions; ignore venv/node_modules/cache/temp/build artifacts unless explicitly needed for offline distribution. Report material missing evidence plainly.
