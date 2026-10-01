# Metamorphic relation catalog v1.0

## Contract and notation

Read SPEC §4 first. Assignment p.1 §2 explicitly requires a contract before MRs; the table there is illustrative and permits replacement. These ten relations are hypotheses about this project's statistics, not universal housing laws.

Let `F(D,q,s)` be a completed execution of the **actual MAS** on immutable dataset view D, normalized request q and seed profile s. `C` denotes its canonical result. `n_m`, `p_m`, `r_m` are monthly observation count, median USD list price and median individual USD/sqft. All compared metrics are selected with identical conjunctions of criteria; transformations operate on raw records before scanning. `G(q,m)` is the qualifying multiset, independently checked by preflight. Month labels, not array indices, align series. `Δ(x,y)=100*(x/y-1)` when defined. Percentage strings contain percentage points, not fractions.

`LEVELS` = month, n, p, r. `DELTAS` = price/ppsf MoM and YoY plus count MoM. `ALL_CANONICAL` = all monthly rows and summary (including rankings when requested). Quality decisions, warnings, narrative, run IDs, input hashes and agent route are intentionally excluded; they may change while valid numerical statistics remain correct.

Every relation has ≥30 distinct **eligible** base requests and all three seed pairs. Query modification for an MR is part of its saved base identity. Candidate requests are not automatically valid tests. Preflight uses a small independent exact selector to check input validity and nonvacuity; it does not replace execution of F or supply its expected outputs. Save the transformation recipe, before/after input hashes, witness rows/counts, compared field paths, each seed pair's outputs and diffs.

## Tolerances and null logic

- Counts, month labels, ranks and exact-invariance serialized strings: exact equality/inequality. Do not use a relative tolerance for integer counts.
- Price/ppsf scale comparison: absolute `0.000003` in canonical USD or USD/sqft. This covers six-decimal half-even serialization under k≤2; arithmetic internally remains exact.
- Additive median USD comparison: absolute `0.000001` USD; ppsf monotonicity uses `0.000003` USD/sqft.
- Percentage invariance: absolute `0.000001` percentage points; expected null must stay null. When one side is null and the other isn't, fail unless the MR explicitly excludes that field.
- Presentation conversion: six-decimal display values within `0.000001` display unit of conversion from canonical values. UI rendered rounded text checked separately with exact half-even formatting fixtures.
- Never allow `abs(a-b)<=tol` to turn null into0. No NaN or infinity is valid. Null-null alone is insufficient to qualify a scalar MR. Report how many numeric comparisons occurred.

## MR01: input row permutation (invariance)

**Transformation:** Fisher-Yates permutation of every raw row in D using the case's fixed transform seed; retain all fields and multiplicities. Do not sort again before passing the file through the actual ingestion/index path.

**Subdomain:** any valid complete snapshot and query; ≥2 qualifying rows and at least one nonnull visible median. Require a different raw order and byte hash while logical multiset is equal. Include odd/even monthly sample sizes across the cohort.

**Relation:** `ALL_CANONICAL(F(D,q,s)) == ALL_CANONICAL(F(T(D),q,s))` exactly. Include summary ranking tie-breaks and delta null patterns. Same seed on source/follow-up; route may differ but final numbers cannot.

**Faults:** first-N truncation, order-dependent median, unstable grouping, wrong index construction, state contamination. A final-output-cache hit that avoids the transformed ingestion path is not an executed follow-up.

## MR02: bijective nominal ID relabeling (invariance)

**Transformation:** independently apply deterministic one-to-one string maps to the domain of `record_id` and `listing_id`. Every occurrence of the same old listing ID receives the same new listing ID. No geography, property type, date, price or size changes. Preserve unique record IDs and the equality partition of listing IDs.

**Subdomain:** valid D/q, at least two distinct IDs, ≥1 selected nonnull monthly median. Require at least one selected identifier to change. Arbitrary ZIP relabeling is **not** allowed: ZIP is a semantic criterion and ranking label.

**Relation:** ALL_CANONICAL exact equality, including counts and ZIP rankings.

**Faults:** numeric inference from ID, ID-based filters, deduplication keyed on an unintended label, identity-leaking selection. Never expect trace record-ID hashes to remain equal.

## MR03: twofold observation replication (invariance of distribution)

**Transformation:** for every raw observation in every month, retain the original and append an exact clone with a new collision-free `record_id='replica-'+old_id` (escape/namespace if needed). Retain `listing_id`. The resulting row count doubles, and every observation's multiplicity doubles. Transform comparison months as well as visible months.

**Subdomain:** record-counting contract in SPEC; no unique-listing metric under test; all originals valid, ≥1 selected row, clone IDs don't collide. Input duplicate `record_id` is an invalid-data robustness case, not this MR.

**Relation:** each monthly n doubles; summary total_observations doubles; p and r unchanged; all price/ppsf percentage changes unchanged; count MoM percentages unchanged including null-at-zero rules; pooled ZIP ppsf/ranks unchanged. Thus the full canonical projection equals the source with only count fields and total multiplied by2.

**Faults:** accidental listing-ID deduplication, biased median under multiplicity, averaging precomputed medians without weights, stale count caches. A business contract that deliberately counts unique properties would require a different MR; document such a revision rather than marking its legitimate behavior a bug.

## MR04: display scale and area units (invariance)

**Transformation:** unchanged D and canonical housing criteria; toggle money USD→USD_THOUSANDS and area SQFT→SQM on the follow-up request. Execute both legs through the standard result/presentation path, even though selection may be cached.

**Subdomain:** nonempty output; at least one nonnull price and ppsf; fixed USD currency identity. This is unit conversion, not a USD→INR exchange-rate test.

**Relation:** ALL_CANONICAL exactly equal; summary percentages and ZIP ranks equal. Presentation median price = canonical USD/1000; displayed price per area = canonical ppsf/0.09290304/1000. If toggling only one display control, apply only its factor. Check the six-decimal presentation output and independent expected formatting; do not assert that changing only the unit label is enough.

**Faults:** filtering in display units, double conversion, ppsf-to-ppsqm multiplication error, rounding before statistics, ranks derived from rounded labels. Include a frontend check that canonical query remains unchanged when toggles move.

## MR05: broaden the raw price band (monotonic)

**Transformation:** from inclusive finite `[a,b]` to strict superset `[max(0,a-10000000), b+30000000]` cents; zero is a legal filter lower bound although valid listing prices are positive. Other criteria and D unchanged. Default candidate base band is $200k-$450k; widened band is $100k-$750k.

**Subdomain:** valid band a≤b with a>0; preflight independently proves `G(q,m) ⊆ G(q',m)` for every visible month and at least one **added** qualifying row in a visible month. At least one source selected row. Increase bounds further in a versioned candidate recipe if no witness, never change post-result to obtain a pass.

**Relation:** `n'_m >= n_m` for all 12 months and total'≥total; require strict n increase in at least one witness month. No monotonic claim about medians, ppsf, ranks or percentage changes; adding cheaper records can lower a median and adding expensive ones can raise it.

**Faults:** exclusive boundary handling, inverted lower bound, stale criteria cache, OR instead of AND filters, display/raw currency confusion. Exact counts; no numeric tolerance.

## MR06: restrict to a strict subset of ZIPs (monotonic)

**Transformation:** choose a nonempty proper subset Z' of the base requested ZIP set Z (default first half of sorted ZIPs, at least 1); keep all other criteria and D fixed.

**Subdomain:** at least 2 requested ZIPs; preflight proves subset membership and ≥1 removed qualifying row in a visible month; ≥1 retained row for nonvacuity. Save source and subset set hashes and witness removed record IDs.

**Relation:** `n'_m <= n_m` for all 12 months, total'≤total; strict decrease in at least one witness month. No relation for global median/rank. If public regional comparisons are enabled, an unchanged retained ZIP's pooled median remains equal, but its ordinal rank may change; the monthly count relation is the primary required assertion.

**Faults:** union/intersection mistake, ZIP integer/string conversion, using all-region counts in a filtered response, cache not keyed by ZIP set. Counts exact.

## MR07: advance the visible window by one calendar month (directional)

**Transformation:** same D and criteria, `window_end'=add_month(window_end,1)`. D covers the incoming month; query length remains exactly 12. Default source end months June/July/August 2026 ensure follow-up ends July/August/September 2026.

**Subdomain:** valid complete visible partitions for both windows; ≥1 nonnull median in overlap; exactly 11 shared month labels. Lookback completeness metadata must be unchanged for every shared month.

**Relation:** for the 11 overlapping calendar months compare **all row fields**, including MoM/YoY. The follow-up's first MoM requires its predecessor outside its visible window; this is intentional. Do not compare first-to-last summaries, pooled regional rankings or raw totals directly. Additionally `total' = total - n_outgoing + n_incoming` exactly.

**Faults:** off-by-one dates, positional series alignment, cropping lookback before aggregation, computing first-row MoM as always null, using12 records rather than 12 months. Window labels themselves must change; null-only overlap is not a useful test.

## MR08: positive multiplicative price scaling (directional)

**Transformation:** scale `price_cents` by rational k from {1.10,1.25,1.50,2.00} over **every snapshot month**, including all comparison periods. Default k=1.25. Use finite source price bands for b001-b010 ($200k-$450k) and unbounded bands for the remaining 20 bases, transforming finite bounds in the follow-up; this tests both supported subdomains. Use exact rational math and require integer-cent products. If q has finite price bounds, multiply both by the same k, requiring integer bounds, so slice membership is preserved. Null bounds remain null. Other fields unchanged.

**Subdomain:** k>1, k≤2, all relevant products representable as integer cents; no hidden outlier cutoff/price bucketing; membership multiset correspondences verified; at least one visible nonnull p/r and one defined percentage comparison. Generated whole-dollar prices make the default factors exact. Do not round scaled cents and then pretend exact scaling occurred.

**Relation:** n and total unchanged; every p'/r' equals k*p/r within canonical3e-6 tolerance. All price/ppsf MoM, YoY, first-to-last and last-month YoY percentages equal within 1e-6 pp; count deltas equal; ZIP pooled medians scale and ranks unchanged. Null masks equal. This is stronger than merely observing positive movement.

**Faults:** hardcoded unit conversion, price filters not transformed, stale value caches, mixed raw/scaled comparison months, early ppsf rounding, count changed by hidden price cap.

## MR09: add a fixed USD amount to one month (monotonic)

**Transformation:** set the base price band to unbounded **before identifying/saving the base query**. Select a nonempty visible month h by fixed recipe (first nonempty month); add d=$1000 (`100000` cents) to every raw observation in month h. All other months, including historical comparison months, stay unchanged. D can contain records excluded by other criteria; transform the whole month consistently.

**Subdomain:** both price bounds null, d>0 integer cents, at least one selected record in h, positive finite sqft, no query using derived price/ppsf criteria. Must prove selected membership equal after transformation. If a query retains a price band, reject it as invalid for this MR; global price-band shifting cannot preserve every other month's membership.

**Relation:** n/total unchanged; `p'_h=p_h+1000` within 1e-6 USD. For h, `r'_h >= r_h + 1000/max_selected_sqft_h - 3e-6`, because every individual ppsf increases by at least that amount. In other visible months p and r unchanged. Do not assert `r'_h=r_h+d/median_sqft`; that is generally false. Do not compare MoM/YoY or window summaries as invariant: h can be a numerator or denominator, affecting other months' deltas. Assert price/ppsf **level** nondecrease across all visible months only.

**Faults:** wrong month mutation, monthly median calculated globally, aggregation of rounded prices, silently retained price-band filters, incorrect ppsf algebra.

## MR10: append only valid observations outside the requested ZIP set (invariance)

**Transformation:** append at least 24 valid observation rows (one per snapshot month) in an allowed ZIP absent from q.ZIPs; use fresh record/listing IDs and deterministic otherwise-valid positive price/sqft/bedroom/type fields. Complete month metadata stays complete. Do not add invalid rows and call their quarantine the test.

**Subdomain:** requested ZIP set is a strict subset of allowlist, ≥1 selected visible observation, appended records provably fail ZIP criterion and at least one lies within visible months. Their other fields may be in-band so ZIP filtering is what excludes them.

**Relation:** ALL_CANONICAL unchanged exactly. Global dataset quality totals and hashes may change; do not compare them. Prove the input gained rows and selected multiset remained equal.

**Faults:** aggregates computed before geographical filter, forgotten ZIP filter in lookbacks or Region Specialist, total-dataset count leaking into query count, cache keyed by row count only.

## Required result representation

`templates/mr_definitions.json` is machine-readable catalog data; `schemas/mr_definition.schema.json` validates it. `schemas/mr_result.schema.json` describes each per-base/per-seed comparison. Every record includes MR/version, base/transform identity, source/follow-up run IDs and hashes, requested/effective seeds, mode/campaign, status, witness/eligibility, compared numeric count, max error, detailed mismatches and evidence paths. An empty mismatch list is meaningful only when an eligible relation was actually evaluated.

Statuses are `pass`, `violation`, `invalid`, `execution_error`. Invalid cases are precondition/transform defects and remain visible outside the violation denominator. Parse/policy/output-contract faults after a valid launch are violations of the observable output contract, with subtype; model unavailable, replay missing, process failure and harness errors are execution errors that block completion. No status is silently converted to pass. See EVALUATION_PROTOCOL for base-level aggregation and proper CI denominator.

## Scientific restraint

Preflight cannot be based on observed source/follow-up failures or chosen to remove failures. Version a defective MR, document why it failed semantically, retain old results, then rerun the revised experiment. Deliberate mutation failures demonstrate test sensitivity; they are not evidence of spontaneous application violations. Zero natural violations are reportable. A comprehensive relational suite still does not prove the absolute correctness of every output.
