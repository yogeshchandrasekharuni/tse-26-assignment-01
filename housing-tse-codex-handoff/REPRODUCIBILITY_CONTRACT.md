# Hashes, replay boundaries and one-command execution

This is an implementation contract. No live-captured corpus or completed campaign is supplied by the handoff. See FAST_AGENT_INTEGRATION and EVALUATION_PROTOCOL for the broader design.

## Stable JSON and identity

For semantic JSON hashes use UTF-8 bytes from `json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)` with no added trailing newline. Inputs contain strings, integers, booleans and null; use exact rational objects instead of floating results. Hash with SHA-256. Save the normalization version. This is a chosen Python serialization convention, not a claim to implement the entire RFC8785 standard.

- `snapshot_sha256`: committed source CSV bytes, exactly as frozen.
- `dataset_view_sha256`: transformed raw CSV/view bytes or canonical deterministic materialization recipe plus its source-byte hash, as specified and versioned. Distinct raw-order views must remain distinguishable through ingestion even if statistics agree.
- `logical_multiset_sha256`: sorted valid row representations retaining multiplicity. ID relabeling legitimately changes this hash; order alone does not.
- `canonical_query_sha256`: dataset-view identity plus visible end, normalized criteria and compare_regions. Exclude display and seed. For distinct-base counting use the **source housing query** plus underlying source dataset ID/hash, not the transformation identity, MR ID, display, run ID or seed.
- `full_request_sha256`: full normalized request including display and seed plus runtime profile; useful for physical execution cache lineage, never for inflating distinct bases.
- `plan_sha256`: semantic plan version, action, strategy, active specialist set/purpose, required-month list and canonical query/view identities. Exclude trace-event sequence references and IDs; store those separately as causal trace metadata.
- `semantic_tool_receipt_sha256`: hash only tool name/version, query/view/selection identities, strategy, required/available month and completeness fields, and **pure mathematical result hash**. Exclude receipt/run IDs, timestamps, durations, filesystem paths, event sequence numbers and other incidental metadata. The exact rational numeric result file itself has no run IDs/timestamps/paths.
- `semantic_prompt_sha256`: exact final instruction/input bytes actually sent, including stable allowed-action schema and upstream **semantic** receipt hashes. Never include the entire volatile JSONL receipt in a model prompt.

Raw trace/receipt files can also have full byte hashes for integrity. Those are different from semantic replay keys. Preserve both and name them clearly. If parallel completion order differs, assemble prompt evidence in deterministic role/month/ZIP order. An event's causal sequence belongs in trace metadata, not the semantic plan or model prompt.

## Decision replay boundary

The cassette stores an actual model response, not an analysis result. A key includes semantic prompt, role instructions/schema, dataset-view/tool-bundle identity, model profile/digest, effective/requested seed, iteration and normalized upstream semantic result hashes. Fast Agent playback returns that recorded response in a fresh role context. The current dispatcher then executes real Python tools and the controller computes the new next state. If a numerical result changes, later semantic prompts normally change; reject the missing new cassette rather than silently continuing with stale decisions.

The gateway between live capture and playback must preserve raw response text and its hash, including captured invalid responses and repairs. Policy-simulation decisions are kept in a different directory and cannot be marked origin=live_captured. Do not key only on role name, iteration or seed. Do not replay final public canonical outputs as the source of statistics.

## Required offline behavior

After documented setup and a genuine live capture, `make reproduce` must:

1. Verify lock/source/schema/prompt/model/cohort/cassette identities and the committed source CSV byte hash; fail if reference lineage is incomplete.
2. Assert an offline profile: no external HTTP/model access, no downloads and no live fallback. Local filesystem/SQLite access is sufficient for Fast Agent's internal playback model; network denial should not prevent this path.
3. Start the same application workflow service used by API/live CLI, selecting replay adapter. Reconstruct all source/follow-up views and execute Fast Agent role playback and actual tools/control flow.
4. Execute all 900 expected logical MR comparisons (ten relations,30 frozen eligible bases,three seed pairs). Source physical reuse can reduce work only under complete identical-input keys and explicit lineage; log actual tool/agent calls. Do not count repeated replay as fresh data.
5. Validate outputs, case statuses, distinct base/seed coverage and nonvacuity witnesses. Build base-level any-seed outcomes, recompute rates and Wilson intervals, and write new summary artifacts.
6. Compare the recomputed semantic headline values against the saved live-campaign reference. Ignore only execution-mode/run-ID/timestamp metadata, never failures, counts, CI bounds, source seeds or MR versions.
7. Return a nonzero status for any missing cassette, execution failure, unresolved infrastructure/harness error, reference mismatch or incomplete minimum. A reproduced observed MR violation is a successful reproduction: exit status must not require zero violations. Print a compact path-linked summary and update no committed reference file automatically.

Use a temporary run directory and atomic renames so partial reproduction cannot overwrite reference evidence. The command must be runnable from a clean checkout after explicit setup without the instructor supplying API keys or pulling a model. If fresh zero-network setup is desired, ship a compatible wheelhouse/container image separately and document architecture/OS constraints.

## Clean-checkout evidence

Save git revision, clean/dirty state, setup command/log, network-block method, reproduction command/log, role/receipt counts, recomputed table hash and comparison report. Also show one sampled source/follow-up trace in replay mode whose tools executed during this run. Merely reading saved cases or rerunning the CI formula is insufficient to establish end-to-end reproduction.
