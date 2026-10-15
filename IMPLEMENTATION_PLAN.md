# Implementation, experiments and reporting plan

Status: G0–G9 are implemented and verified. The full live capture has900 eligible comparisons across300 MR/base panels and all three seeds; the independent integrity audit passed. Ranked diagnosis, all 900 comparisons in a fresh clean-checkout offline run, current local Langfuse readback/browser proof, desktop/mobile verification, the twelve-page final PDF/all-page inspection and actual submission checks are complete. See EVIDENCE_INDEX.md for proof and historical failures. The original assignment governs coursework requirements.

## Agreed shape

- Python 3.15.0, fast-agent-mcp 0.10.45, FastAPI/Pydantic, React/Vite/TypeScript. Use the exact locked environment for evaluation; rechecking latest releases does not silently alter a frozen campaign.
- One parent Orchestrator exposed to UI/API/CLI/harness. Register Price, Supply, conditional Region, Reviewer and Composer as Fast Agent children through `@fast.agent(agents=[...])`. No child is called directly by an external entrypoint.
- Keep a small Python state/validation controller inside that boundary. Bind trusted data/query/selection arguments, enforce capabilities, dispatch real tools, aggregate receipts, and record decisions/actions. It does not replace the agents' decisions with scripted role stubs.
- Canonical math is deterministic and exact. Models select allowed plans/intents/facts; they do not supply medians or counts.
- Default model: the already available local Qwen 3.5 9B Q4_K_M, through three verified seeded profiles. Freeze full digests, resolved parameters, Ollama version and hardware. The model choice remains contingent on the production pilot's schema/throughput evidence.

## Gates and deliverables

| Gate | Implementation and evidence | Acceptance before proceeding |
|---|---|---|
| G0: framework proof | Native planner vs agents-as-tools comparison, named calls, real tools, real feedback, seeds/isolation, strict offline playback | Evidence in FRAMEWORK_FINDINGS.md. Selected parent/child pattern works. Separate the native final-return failure and integration fixes from completed capabilities. |
| G1: contracts and core data | Define typed request/output/plan/decision/tool-receipt contracts before MRs. Implement calendar arithmetic, exact medians/ratios/percentages, six-decimal half-even serialization, filtering and ingestion. | Hand-calculated tests include even medians, median-of-ratios, raw inclusive bounds, identity multiplicity, zero/null comparisons, unavailable lookbacks and ranking ties. Unknown fields/invalid datasets fail. |
| G2: frozen snapshot | Implement the specified seeded 24-month generator; commit 34,560-row CSV, config, provenance and completeness manifest. Build indexed/full-scan access through shared filters. | Two regenerations produce identical bytes/hashes. All generated rows valid. Index/full-scan record multisets and receipts agree on clean data. Missing partitions differ from empty selections. |
| G3: production MAS | Build the sole `run_analysis` service behind Orchestrator; real child calls, typed intents, deterministic aggregation, fact registry/Composer, immutable request, traces, errors and budgets. Close SDK/framework nested-retry issue. | Normal and sparse paths; live omission control; initial→full_csv with Region activation; unchanged query; new specialist receipts; no forbidden broadening; correct limited result. At most two distinct refinements, one repair, one transport retry verified separately. |
| G4: one-MR live/replay pilot | Implement MR01 through the production service. Run 3 distinct bases × 3 paired seeds, capture all parent/child decisions and native tool calls, then rerun offline. | Tools/control flow/comparisons execute again; changed prompt/schema/tool/upstream receipt/seed fails closed. Live/replay outputs agree. Record calls, tokens, repairs, errors and elapsed time before budgeting the larger campaign. |
| G5: freeze full experiment | Implement all 10 MRs with independent eligibility/nonvacuity preflight, deterministic transformations, exact projections/tolerances and mutation controls. Freeze snapshot/contracts/prompts/model/locks/MR/cohort/seed hashes. | Exactly 30 distinct valid source query hashes per MR; every transform has an effect/membership witness. Replenish candidates deterministically before seeing model outcomes. Include useful sparse/dense and odd/even cases. Invalid controls are invalid, not passes. |
| G6: API and interactive UI | FastAPI background jobs plus SQLite metadata and immutable artifacts. Explore, Workflow, MR Results and Data/Provenance views, generated TS contracts, charts/tables, trace drilldown and exports. | UI and harness use the same service. Run→12 rows/chart→trace→export browser smoke at desktop and 390px. Clear synthetic/live/replay/limited/error states; display toggles do not change criteria or recompute canonical stats. |
| G7: headline execution | Run frozen 10 × 30 × 3 campaign. Save every attempt and disposition. Summarize raw immutable cases separately. | 900 logical comparisons; three complete paired outcomes for each of 300 MR/base combinations; zero unresolved infrastructure errors for official-complete rows. Failed eligible model contracts count as violations. |
| G8: diagnosis and reproduction | Rank actual violated MRs; inspect rows, decisions, receipts, field diffs and minimized cases. Reproduce the complete corpus offline from a clean checkout after setup. | Recomputed counts, failures and Wilson table match the saved live reference. Missing cassettes fail. Fewer than three nonzero relations is stated honestly; injected controls are separate. Preserve pre/post-fix campaigns. |
| G9: report and submission | Render and visually inspect the final 10–12-page PDF, editable diagram sources, README, NOTEBOOK, AI_USE, evidence index, code/locks/data/seeds. | Every measured claim has an artifact. Page-count/completeness/hash checks pass. Documented make targets have actually run. No invented author names or deadline hour. |

G6 can overlap harness development once the production contracts/service are stable. Final numerical claims and interpretation wait for G7/G8. No public deployment, paid API, scraping, authentication, alternative city, free-text parsing or visual effects are needed.

## Experiment protocol to freeze before headline execution

- Ten MRs from the handoff catalog: reorder, nominal-ID relabel, observation replication, display units, broaden price band, restrict ZIPs, advance month window, multiply prices, add to one month, append out-of-scope ZIP records.
- Distinctness is the normalized source housing query plus underlying source snapshot identity. Display choices, random seeds, run IDs and transformed row orders do not create new bases.
- Use paired source/follow-up seeds 104729, 130363, 155921. Dataset generator, cohort selection and transformation randomness have separate recorded seeds.
- Source and follow-up use immutable data views and fresh parent/child contexts. Every follow-up executes the workflow. Any exact source reuse across MRs must have full semantic keys and explicit lineage.
- Preflight uses an independent simple selector to prove completeness, selected membership and nonidentity/effect witnesses. It must not share production median/delta/comparator logic or select cases based on observed failures.
- Implement catalog-specific null masks, exact integer/string checks and declared rational tolerances. Do not compare whole responses, narratives or route choices as numerical invariants.
- Statuses: pass, relation/output-contract violation, invalid precondition, execution_error. Model parse/policy failures on eligible cases are violations; unavailable inference/replay or crashed tools are execution errors. Preserve all attempts and block incomplete rows.
- Primary outcome per base is **any violation across the three fixed seed pairs**. Primary denominator is 30 completed bases, not 90 correlated pairs. Compute nominal 95% Wilson intervals; report descriptive pair/per-seed counts separately. At 0/30, the upper bound is approximately 11.35%, so zero observed failures cannot support a below-1% claim.
- Describe overlap among slices and the designed convenience cohort. These intervals summarize the frozen workload under nominal assumptions; they do not establish representative Dallas-market or arbitrary-model reliability.

## Evidence layout and reproduction boundary

- `data/frozen/` and `data/manifests/`: generated CSV bytes, schema, provenance, completeness and hashes.
- `artifacts/traces/`: requests, plans, model decisions, tool invocations/receipts, aggregate/review/finalization events with causal links.
- `artifacts/cassettes/`: only genuine live model captures with exact semantic lookup and raw response integrity. Policy simulation is stored separately.
- `artifacts/campaigns/<campaign>/`: frozen manifest/cohort, immutable cases, witnesses/transform recipes, source/follow-up outputs, raw outcomes, base summaries, headline CSV/JSON, runtime and artifact hashes.
- `artifacts/rca/`: actual ranked findings, minimal reproducers and competing explanations. Separate injected controls do not enter headline counts.
- `make reproduce`: after setup, deny network/model access, re-materialize data views, invoke Fast Agent playback for recorded decisions, rerun current tools/controller/MRs, rebuild the table and compare semantic headline values. It may not load saved final outputs as its arithmetic source.

## Reporting alongside implementation

Maintain NOTEBOOK.md and AI_USE.md with actual commands, failures, corrections and evidence at every gate. Keep a requirement-to-evidence index as the implementation lands. Build the report skeleton and diagrams while contracts/workflow stabilize; fill the results table, diagnoses and conclusions only from executed campaigns.

Use the handoff's 12-page allocation including title/references: system/topology and actual loop; data/output semantics; ten MRs/subdomains/tolerances; evaluation design; results/CIs; actual RCA or honest zero/fewer-failure discussion; threats and half-page AI reflection; reproduction/evidence references. Names of the two authors remain user-supplied submission metadata and do not block implementation.

## Completion record

The frozen full campaign launched from commit 8a50f75 at 15:17:57 UTC on 25 September 2026 and completed all 900 at 18:54:06 UTC on 6 October 2026 after the documented reboot recovery. Frozen production/evaluation inputs remain unchanged. All 690 numeric pairs satisfy their projections;210 pairs retain eligible output-contract violations. The initially clean revision 8eb6727d completed full offline reproduction at 20:29:30 UTC, followed by the final report, all-page visual inspection and successful submission target. Actual command times/hashes are in reports/data/clean-checkout.json and artifacts/verification/final-delivery-v1. The pilot's210 model decisions and six refinements remain pilot evidence only; no evaluated behavioral mitigation or extra model sample is claimed.
