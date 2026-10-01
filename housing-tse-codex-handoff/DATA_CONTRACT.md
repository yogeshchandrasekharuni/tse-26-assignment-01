# Frozen data and arithmetic contract

## Source and intended use

The assignment p.1 permits a synthetic feed, p.3 explicitly suggests generating monthly Dallas listings, and p.4 permits documented assumptions. Use a generated Dallas-themed test feed. We choose it because it gives actual monthly observation semantics and exact provenance, not because it predicts or reproduces Dallas market behavior. Never cite Kaggle, Zillow or a live site as the source of generated rows. Original data-source alternatives on assignment pp.3-4 are references only.

## Raw row schema

`schemas/listing.schema.json` defines a row. CSV columns, in order:

`record_id,listing_id,month,zip,property_type,bedrooms,sqft,price_cents`

- UTF-8, LF line endings, header present, comma delimiter, RFC4180 quoting, no BOM. All integer fields have base10 integer text; JSON equivalents are numbers. No currency symbols or commas inside numeric values.
- `record_id`: nonempty ASCII identifier, unique across the entire snapshot. It is not a numerical or geographical feature.
- `listing_id`: nominal property/listing label. Repeats across months are expected; repeated IDs are never deduplicated by numeric tools.
- `month`: `YYYY-MM`, from explicit observation date, the UTC monthly snapshot label. Generated base snapshot records need no invented sale dates. If a future timestamped importer is used, require timezone-aware timestamps, convert to UTC, then bucket by calendar month; naive timestamps fail.
- ZIP allowlist: 75001, 75006, 75019, 75024, 75034, 75038, 75063, 75080, 75093, 75201, 75204, 75214. These are synthetic stratification labels, not a claim of complete DFW coverage.
- property_type: `single_family`, `condo`, `townhouse`; bedrooms integer1..5; sqft positive integer; price_cents positive integer. Headline generation stays within sqft500..5000 and $80,000..$2,000,000; MR transformed datasets may exceed these generator ranges but remain positive valid integers.

## Ingestion and eligibility

1. Verify file SHA-256 against manifest; parse strict columns/types. A duplicate record_id or malformed header invalidates the dataset (stop; no arbitrary first/last-wins behavior).
2. Quarantine independently invalid rows and emit `{line,record_id,reason,raw_hash}`; raw file stays immutable. All headline generated rows should pass. Invalid-price fixtures are separate robustness tests. Report raw/valid/quarantined counts by reason.
3. Check manifest month presence/completeness against parsed records. A complete partition can have zero records and must be marked explicitly. A missing file partition must not silently become a zero month.
4. Build a read-only partition index; store index content hash and source CSV hash. Filter logic is shared by full-scan and indexed paths, with parity tests.
5. Determine the union of requested visible and comparison months. Apply identical non-date criteria to each partition: ZIP → type → bedrooms → sqft → **raw price_cents band** → aggregate. Filtering precedes ppsf and median computation. No filter uses rounded display money or ppsf. Since filters are conjunctions, order must not change semantics; this fixed order makes tracing simpler.
6. Sort selected record IDs only for selection hashes; numerical sorting is by metric value. Source input row order must not leak into sampling, truncation or medians. Do not canonical-sort transformed CSV before the ingestion path if doing so would skip testing order handling; retain a separate input byte hash.

Inclusive bounds include exact equal endpoints. `null` upper/lower means infinity in the appropriate direction. Query validity is independent of whether records match; all-empty queries are valid UI queries but generally ineligible for scalar MRs without a meaningful witness.

## Generator recipe to implement and freeze

`templates/generator_config.json` records constants. Use Python's deterministic `random.Random(20261016)` under the locked Python version; record its algorithm/runtime version. A fully stable alternative is a tiny documented hash-based PRNG, but do not change it after freeze.

Iterate24 months in ascending order, twelve ZIPs in listed order, and120 observation slots per ZIP/month: **34,560 records**. This is large enough for coverage across criteria; extend deliberately if preflight finds fewer than 30 valid effectful cases. Regeneration must exactly match committed CSV bytes, including ID formatting and record order.

For month index t=0..23, ZIP index z=0..11, slot i=0..119:

- `record_id=f'obs-{t:02d}-{z:02d}-{i:03d}'`; `listing_id=f'listing-{z:02d}-{i:03d}'`. Reusing listing IDs across months explicitly models repeated monthly observations; inventory size is fixed by design.
- `property_type = ['single_family','condo','townhouse'][i % 3]`; `bedrooms=1+(i % 5)`.
- `sqft = 650 + 380*bedrooms + 30*(z % 4) + randint(-120,120)`; integer and strictly positive.
- `base_ppsf_cents = 13500 + 850*z + (0 if single_family else 1500 if condo else 750) + randint(-1800,1800)`.
- Trend basis points: `trend_bp=10000+28*t+seasonal_bp[t%12]`, with seasonal list `[-80,-60,0,60,120,160,130,100,30,-20,-60,-100]`.
- Compute `raw_price_cents=Fraction(sqft*base_ppsf_cents*trend_bp,10000)`; round half-even to the nearest **100 cents** (whole USD), with the exact rounding helper used by serialization. No float sin(), lognormal draw or unrecorded platform math. The resulting prices should fall within the stated generation range; assert rather than clip silently.
- Do not artificially call this the actual Dallas seasonality or growth rate. It is a deterministic scenario, with intentional composition/noise.

Random draw order for each row is sqft jitter then ppsf jitter. No other random calls in the generator. Write exactly the column order above. The byte-level snapshot is the artifact; generate a manifest after writing, not before. `created_at` is provenance outside the CSV and excluded from deterministic identity checks. Extend dataset by creating a new version, never rewriting the v1 manifest in place.

## Manifest to produce

`templates/dataset_manifest.template.json` has nulls for values that only implementation can measure. Replace nulls honestly after generation. Required: version, source_kind=synthetic, generator path/hash/config hash/seed/runtime, expected and actual row counts, bytes SHA, logical multiset SHA, month completeness map, ZIP/type enums, schema version/hash, valid/quarantined counts, limitations, and license chosen by the authors for their generated data. Do not fabricate a measured checksum in advance.

Two identities matter: byte hash changes under MR01 reordering; a canonical logical **multiset** hash sorts validated row representations and preserves multiplicity. MR02 relabeling also changes logical row hash but does not change numeric statistics. Cache keys must never use only business listing IDs or only query text. Query hash excludes presentation preferences for selection-cache purposes, but full request hash includes them for model/replay lineage. Record both.

## Edge cases and exact examples

`fixtures/metric_cases.json` supplies small oracle cases. For prices $100/$200 and sqft1/4, individual ppsf values are100/50, median75; median price150 / median sqft2.5 equals60 and is wrong. Even medians of integer-cent values can produce half-cent dollar outputs. Monthly median is computed separately, not over the entire visible window. Zero selected records means null medians. Complete empty months and unavailable source months are different.

YoY uses the identical month in the previous calendar year, not first-to-last visible rows and not previous12 records. Month arithmetic is calendar arithmetic across December/January and leap years; never subtract365 days. Store timezone conversions only at ingestion boundaries.

## Transform persistence

Store transformation recipes and input hashes, not thousands of redundant CSV copies when a deterministic materializer suffices. Each leg must see an immutable dataset view. MR01 randomizes raw record order with its fixed transform seed; MR02 maps nominal IDs; MR03 clones all observations with new record IDs; MR08 scales prices in **every** snapshot month including lookbacks; MR09 shifts one visible month's prices; MR10 injects only records outside the accepted query slice. All materialized views have manifests and share the same source completeness map unless explicitly testing data integrity. A transformed snapshot is never marketed as an independent data source.

## Limitations to disclose

Synthetic structural regularity, fixed inventory, no real addresses/seller behavior, no missingness in the clean headline snapshot, repeated listing IDs, chosen ZIP subset, designed seasonality, and controlled price support all limit external validity. Passing MRs tests relational consistency on this workload, not market realism or absolute correctness. An optional real data cross-check must be separately sourced and cannot replace the frozen per-observation experiment.
