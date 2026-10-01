# Final report: 12-page template and evidence map

The assignment p.2 §3 requires10-12 pages. Target **12 total pages including title/references**, unless the instructor gives another counting rule. Do not use an uncounted cover or oversized appendix to evade the limit. Repository evidence can be more extensive than the PDF. The template below allocates real space, including half a page for the required reflection. This file is a template, not a finished report.

| Page | Content | Required evidence |
|---|---|---|
|1|Title, names/team of 2, task, frozen experiment summary, concise scope/assumptions|assignment citation, repo revision, snapshot/model/campaign hashes; no invented abstract results|
|2|System architecture, role capabilities, marked cycle C1 and dependency rationale|updated topology diagram, prompt/schema versions, ARCHITECTURE|
|3|Workflow and actual loop firing; stop/iteration signals and bounded behavior|actual live JSONL excerpt with iteration, strategy change, Region activation, unchanged query hash; fixture/injection label|
|4|Dataset generation/source,24-month coverage, limitations, exact output contract and date semantics|frozen manifest/hash, generator config, coverage plot, count/median/ppsf/MoM/YoY definitions|
|5|MR01-MR05 compact catalog: relation, subdomain, tolerance, fault rationale|versioned MR catalog and exact metric projections|
|6|MR06-MR10 catalog and counterexample discussion for tempting invalid properties|additive ppsf caveat, price-band scale semantics, shift lookbacks, replication grain|
|7|Evaluation protocol, distinct cohort,3 seed pairs, modes, cost, CI unit and assumptions|eligible manifest, seed manifest, runtime logs, base-any-seed Wilson formula, invalid/error treatment|
|8|Actual headline table of 10MRs with base counts/rates/95% CIs and seed-pair secondary counts; meaningful result discussion|artifacts/evaluations/<campaign>/headline.csv,json; reproducibility lineage and CI widths|
|9|RCA of highest two violated relations, compact evidence tables/minimal cases|actual failing rows/decisions/receipts/diffs; categories and pre/post-fix evidence|
|10|RCA of third relation, or honest fewer-than 3fallback; separate sensitivity controls if needed|artifacts/rca/MRxx.md; actual observed versus injected distinction|
|11|Threats to validity (~half page); required AI/LLM reflection (~half page)|limitations below, AI_USE/NOTEBOOK and actual execution facts|
|12|Reproduction instructions/evidence index, conclusion at supported strength, references|clean checkout log, hashes, make reproduce output, sources register|

## Required measured table columns

MR ID/family; distinct bases eligible/completed; fixed source/follow-up seed list (or shared footnote); violating bases x/n; rate%;95% Wilson lower/upper%; seed-pair violations/total (descriptive); invalid and unresolved-error counts; mode/campaign. To fit page8 use shared seed/mode notes and move detailed case rows to repository. Mark an incomplete experiment INCOMPLETE, never omit the missing rows to make a complete-looking table. No placeholder numeric results or synthetic “typical” violation rates in the final PDF.

## Example paragraph placeholders to fill after execution

- Dataset: “We generated [actual count] monthly observation records for [months], using [generator version/seed]. These are synthetic scenarios; they do not estimate real Dallas market movement. The frozen CSV SHA-256 is [hash].”
- Workflow: “At trace [actual ID], Reviewer emitted [decision/signal] at iteration[...]. Planner changed[...], causing[actual tool/agent actions]. The query hash stayed[...].”
- Results: “On[actual n]distinct bases with[seed list], MRxx violated on[x]bases under at least one paired seed; the nominal95% Wilson interval was[actual bounds]. This[does/does not]support[limited claim].”
- Diagnosis: “The first divergence was[field/path]in[receipt/decision]. Evidence[link]supports[category], while[alternative]was excluded by[check].”

These sentences are drafting aids. Delete brackets and replace only with measured facts; otherwise say unavailable/incomplete.

## Threats to validity to discuss concretely

- Construct: observations versus unique properties; asking-price medians versus sale prices; first-to-last versus YoY; exact nominal semantics; properties outside MR subdomains; MRs do not establish absolute truth.
- Internal: shared numerical helpers/reference preflight bugs; transformed filter errors; stale caches; changed prompts/model; trace fidelity; replay corpus matching and output shortcuts; seed propagation and nondeterministic kernels.
- Statistical conclusion: only 30designed bases, threefixed seed conditions, overlapping slices/correlated outcomes, nominal Wilson assumptions, selection of top 3, multiple properties explored, CI widths and zero-failure upper bound. Avoid significance claims without a predeclared test.
- External: synthetic regularity, fixed inventory and chosen ZIPs, one local model/hardware/provider, one frozen period, no live source or representative market claim.
- Reproducibility: dependencies/model digests, first-time setup versus offline rerun, replay reproduces recorded decisions rather than fresh model samples, hardware affects live repeatability, any missing/failed cases.

## Half-page reflection: required prompt

Write about200-250words grounded in AI_USE.md: which architecture, schemas, MR hypotheses, code scaffolding, narrative and tests an LLM could have drafted without running; which claims required actual generated bytes, live decisions, feedback trace,900 paired comparisons, recorded seed/model versions, violations/CIs and root-cause evidence; at least one real AI mistake and how it was detected (or explicitly state none documented); boundaries between authored fixtures, simulation, capture and measured execution. Do not claim an LLM itself could not calculate a CI: the missing element is observed outcomes and empirical verification, not arithmetic ability. Disclose this handoff as substantive AI assistance.

## Final QA

Render PDF pages and inspect readable diagrams, tables, footnotes and reference links. Verify exactly 10-12 pages and no clipped table/text. Every measured claim must link to a committed artifact or a reproducible command; each source claim gets assignment page/section or official-source URL. Include actual two authors' names; do not invent them. Check report table hashes against reproduced output and keep a short evidence index in the repo.
