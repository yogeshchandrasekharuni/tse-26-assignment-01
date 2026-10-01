# Evaluation, uncertainty, cost and diagnosis

## 1. Freeze the experiment

Assignment pp.1-2 requires at least 30 distinct base inputs **per MR**, at least 3 fixed recorded seeds for nondeterminism, violation rate plus95% CI, and evidence-based diagnosis of the three most violated relations. Freeze snapshot, schema/MR/prompt versions, model digest, dependency locks, seed manifest and the final eligible-base manifest before the headline run. Any correction creates a new campaign ID; retain the previous evidence.

Use `templates/seed_manifest.json`: paired source/follow-up seeds104729,130363,155921; same seed on each pair to reduce irrelevant variation. These are three fixed evaluation conditions, not90 independent bases. Dataset generation, case/transform selection and optional bootstrap have separate named seeds; no calls to unseeded global random state. Set/record PYTHONHASHSEED and deterministic sorting, while recognizing that hardware/model kernels may remain nondeterministic.

## 2. Distinct bases and preflight

`templates/base_candidates.json` contains30 structured query candidates: ten slice definitions crossed with three end months. All use strict ZIP subsets with at least 2 ZIPs. They are **design candidates, not claimed valid evaluated inputs**. For MR05 attach the canonical narrow price band; MR08 bases b001-b010 use the same finite band with transformed follow-up bounds and the other 20 bases are unbounded; MR09 uses no price band; MR07 advances the window. Save the actual MR-specific source query and its canonical housing-query hash (dataset/window/criteria/compare flag; exclude run IDs, seed, display and MR ID). Do not inflate distinctness with alternate random seeds, row reorderings, output labels or display settings. Across different MRs source queries may overlap; within one MR all 30 hashes must differ.

Preflight independently validates schema, dataset completeness, transformation determinism, source/follow-up selection correspondence, and each catalog witness. Save row-set/count witnesses. Reject/replenish invalid **before** running the model campaign. Generate additional deterministic candidates with a versioned recipe if needed; never reword criteria or pick a new seed because an eligible case violated a relation. Require coverage across sparse/dense, multiple ZIP/type/bedroom/window/price combinations, and odd/even median cardinalities. The designed cohort is a convenience workload, not a random representative sample of all possible Dallas queries. State this explicitly.

Use exactly 30 frozen valid bases initially. An optional predeclared expansion to60 or100 is allowed for precision, but never stop opportunistically after a favorable result. If precision is inadequate at30, report the width and limited conclusion. Record the sampling design and frozen cohort. Independent mathematical preflight must not share the implementation's median/percentage comparator code; use simple exact reference logic only to establish validity and witnesses.

## 3. Run each pair end to end

For each `(MR,base_id,seed_pair)`:
1. Materialize/hash source D/q and transformation metadata. Start fresh model contexts.
2. Execute the production workflow through its application service; retain decisions, receipts, canonical output and trace.
3. Materialize/hash follow-up D'/q'. Start fresh contexts and execute the same service.
4. Validate both output contracts and lineage. Compare only the MR projection using exact/toleranced rules.
5. Atomically append a case result and detailed diff. Record every model/repair/transport attempt. Never turn an exception into an all-null successful result.

Model decision output invalid after one explicit repair, forbidden plan action or invalid canonical output on an otherwise eligible request is `violation` with `violation_kind=output_contract` (there may be no numeric comparison). A numerical property failure is `violation_kind=relation`. An unavailable model/server, missing replay item, crashed tool, unreadable input or harness exception is `execution_error`; it prevents a complete official row. `invalid` means precondition failure and is outside the semantic denominator. Distinguish these in tables. Fixing infrastructure and rerunning the **same** case is permitted; keep failed attempts and final disposition, no silent seed substitution.

Do not warm-start the follow-up from source chat history. Share the same underlying frozen feed except the explicit transformation. Deterministic numeric selection caches may be reused only with complete content keys; source analysis reuse across MRs requires equal full semantic input/profile/seed and visible cache lineage. Each logical pair remains recorded, but reused source execution is not counted as a fresh statistical replicate. Disable final-output cache on follow-up in the headline suite.

## 4. Primary rate and CI: base input is the statistical unit

For an eligible base i, let `v_ij=1` when paired seed j violates the relation or output contract, else0. Define `Y_i=max(v_i1,v_i2,v_i3)`: **base violates under at least one of the three fixed seed pairs**. All three paired outcomes must be available; infrastructure errors leave that base incomplete, even if a violation was already seen.

Primary headline: `x=sum_i Y_i`, `n=number of eligible completed bases`, `p_hat=x/n`, with a two-sided95% Wilson score interval on **n bases**. Official-complete rows require n≥30, all expected seed pairs, zero unresolved execution errors and documented invalid candidates. Do not write `n=90` because there are3 seeds. The estimand is explicitly failure under any of this fixed seed panel, not probability for an arbitrary new random seed.

With z=1.959963984540054, d=1+z²/n:

```
center = (p_hat + z*z/(2*n)) / d
half   = z/d * sqrt(p_hat*(1-p_hat)/n + z*z/(4*n*n))
CI     = [max(0, center-half), min(1, center+half)]
```

n=0 produces no rate/CI, never0%. Calculate full precision, store at least 12 significant digits, and round only presentation. Known checks:0/30 has upper≈0.113513;15/30 is≈[0.331541,0.668459];30/30 has lower≈0.886487. These are mathematical anchors, not assignment results. Reference: [NIST confidence-interval discussion](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

Secondary descriptive measures: seed-pair violations/valid seed-pairs (nominal90 per MR), each seed's base-level rate, contract-fault count, execution-error count, invalid count, feedback frequency and runtime/cost. Do not attach a naïve Wilson90 interval to correlated seed runs. If a seed-averaged interval is requested, bootstrap whole base clusters (resample i and retain all its seeds;10,000 resamples, fixed bootstrap seed) and label it secondary. Avoid presenting a degenerate bootstrap0/0 as proof of no risk.

### Dependence and interpretation

Grouping seeds removes pseudo-replication within a base. Distinct query slices can still overlap the same synthetic records, share a model, and share source executions. Wilson's nominal binomial coverage assumes independent comparable Bernoulli units and a sampling interpretation; the convenience cohort does not guarantee this. Present the interval as a **nominal base-level uncertainty summary for the frozen workload**, disclose cross-base dependence/nonrandom sampling, and do not generalize to all cities, live feeds or models. A seed-cluster bootstrap alone does not cure cross-base overlap. Add a sensitivity table by end-month/slice group if useful, without claiming it establishes independence.

At0/30, the upper bound is about11.35% for this base-any-seed outcome, so do not conclude the system has <1% violation risk. The instructor's request to consider whether a CI is sufficiently tight is answered with the actual width and a restrained claim;30 is a minimum, not automatic statistical adequacy.

## 5. Output files

Each campaign writes:
- `manifest.json`: git revision/dirty state, snapshot/schema/MR/prompt/lock/model hashes, exact commands, environment, seeds, cohort hashes, mode, start/end UTC and completion status.
- `cases.jsonl`:900 expected logical comparisons for 10*30*3 with status and trace links.
- `base_summary.jsonl`:300 base/MR outcomes with all seed-pair links.
- `headline.csv` and `headline.json`:10 rows including family, attempted/eligible/completed base counts, seed values, x/n, Wilson bounds, seed-pair counts/rate, invalid/error/contract counts, run mode/campaign lineage.
- `coverage.json`: month/ZIP/type/bedroom/cardinality coverage and nonvacuity counts.
- `runtime.json`: logical/physical source/follow-up executions, role calls, repair/feedback counts, numeric-cache hits, provider requests/tokens if available, observed duration; no invented prices for free local inference.
- `artifact_hashes.json`: SHA-256 of outputs, raw decisions, traces, receipts, cassettes and transformed-input recipes.

Write immutable case files then build summaries by reading them; aggregation must be a separate deterministic step and must check duplicates/missing keys. Keep raw outputs after bug fixes under prior campaign IDs. Headline production rows and injected-control rows have different campaign IDs and appear in different tables.

## 6. Live versus replay versus simulation

A **live** campaign records actual role decisions from Fast Agent+model. A **replay** campaign strictly retrieves decisions from that campaign, loads them through Fast Agent playback, re-executes the Python tools/control flow and recomputes MR outcomes/CIs. Replay establishes reproduction of that observed decision panel, not new model behavior or an additional90 samples. Report both modes and their lineage. A **policy simulation** uses manually authored decisions only for testing orchestration; label it auxiliary and exclude it from empirical conclusions.

Every cassette key covers role, semantic prompt bytes/hash, allowed-action schema/tool versions, model/profile/seed, iteration, dataset view content/selection inputs and prompt version. Remove volatile run IDs/timestamps before prompting, not after hash matching. Include earlier tool-result hashes that influence the decision. A mismatch is `REPLAY_MISS`; no nearest-match cassette, live fallback, fabricated JSON or loading final canonical outputs. Mutating numeric tool output may invalidate later decision keys; that is correct, not evidence the MR killed a fault. Use targeted mutation tests with declared simulation/capture rather than weakening replay matching.

## 7. Evidence-based root-cause analysis

Rank MRs by primary base-level violation rate descending, then violating-base count descending, then MR ID ascending. Select the top 3 from the actual headline table. Within each select representative failing base/seed and, where useful, a passing neighbor. Preserve full original case, record lineage and a minimized reproducer. Classify with evidence:

1. Agent/aggregation fault: raw/selected rows are valid, contract and MR are sound, but a decision or tool/aggregation path contradicts them. Show decision, receipt and first divergent field.
2. Data artifact: inspect raw row and provenance; demonstrate malformed/misbucketed or business-duplicate behavior that explains the result. Do not blame data without a concrete row.
3. Ill-conceived MR: provide a small mathematical counterexample or violated precondition, revise catalog version, retain initial finding and rerun; do not silently erase it.
4. Harness bug: prove transformation/comparator/alignment/denominator error via minimal fixture; fix and rerun both affected and regression cases.

Each `artifacts/rca/MRxx.md`: observed rate/CI and campaign, exact case/seed/paths, mismatch table, minimal input, trace first divergence, competing explanations considered, category/evidence, patch or revised hypothesis, rerun delta, remaining uncertainty. Use `templates/RCA_TEMPLATE.md`.

If fewer than 3 MRs have nonzero violations, say so. Discuss zero-violation top-ranked MRs as consistency evidence/limits, and use explicitly labeled fault-injection sensitivity controls for diagnostic practice. Do **not** manufacture natural violations to fill a report section. If a control is added to demonstrate diagnosis, its mutation/expected kill/observed trace is reported outside the headline denominator.


See [REPRODUCIBILITY_CONTRACT.md](REPRODUCIBILITY_CONTRACT.md) for exact hash projections, volatile-field exclusions and the offline command acceptance protocol. Upstream **semantic** tool-receipt hashes exclude run IDs, durations, paths and trace sequence references; full byte hashes remain separate integrity evidence.
