# Preliminary Composer caveat omission

The fresh, untransformed source fails after a genuine refinement and Reviewer acceptance. Its broadened-price follow-up completes. The eligible pair is an output-contract violation with no complete numerical comparison. This is a newly observed Composer policy mechanism, separate from the earlier purpose-literal and Reviewer-schema failures; it is not a final ranking or evidence that price-band widening caused an arithmetic error.

The source covers August 2025–July 2026. An independent raw calendar/count check finds 26 visible observations and confirms that required comparison months August/September 2024 lie outside the frozen snapshot, which begins in October 2024. The trusted Composer context therefore requires `SYNTHETIC_DATA`, `SPARSE_SUPPORT` and `UNAVAILABLE_LOOKBACK`. Every selected fact ID is available, including final-month year-over-year change; unavailable early comparison months do not make that final-month fact unavailable.

The parent delegates with a shortened `required_caveats: SPARSE_SUPPORT` hint. Composer also receives the full trusted context and its instruction explicitly requires `caveat_codes exactly required_caveats`. Its response 014 selects four available facts and only `SYNTHETIC_DATA`/`SPARSE_SUPPORT`, omitting `UNAVAILABLE_LOOKBACK`. The shape is valid `ReportDecision` JSON, so event 24 records successful schema validation. The subsequent policy check rejects the missing caveat at event 25 with `AGENT_POLICY_ERROR/ACCEPTED`. No schema repair is attempted, composition is not written and the Orchestrator returns no final analysis.

The evidence isolates the violated obligation: all selected facts are grounded, no extra caveat is present, and exactly one required caveat is missing. The parent's incomplete hint is a plausible coordination contributor, while the child's complete authoritative context remains visible. This single capture cannot establish a unique causal attribution or demonstrate a prompt mitigation. The expected source-availability condition is legitimate; the guard correctly prevents publication that omits it.

Strict current-service playback matched all 15 decisions with zero network attempts. Both initial tools and all three refined tools execute afresh. All five result JSON objects and result hashes match their live records; receipt duration, identifiers and paths differ. The replay reaches the same accepted review and caveat rejection without composition/final output. The new integration regression supplies only manifest, terminal and cassettes, removing saved tool results, receipts, trace and final output before playback.

[minimal-boundary.json](minimal-boundary.json) is an explicitly constructed boundary-only reduction: four required report fields, one available fact ID and the same single caveat omission. Its complete-caveat control is schema-validated separately. It does not claim a full-system minimized dataset, observed model repair, additional sample or successful mitigation.

Evidence:

- [Actual strict playback](20261007T061629Z/comparison.json) and [command output](replay.log).
- [Executed independent/source boundary check](check_composer_boundary.py), [output](boundary-check.log) and [bound diagnostic](boundary-diagnostic.json).
- [Original complete case](../../campaigns/headline-live-v1/cases/MR05-b020-s130363/result.json), including its failed source and completed follow-up.
- [Minimal-capture regression and actual browser/check proof](../../verification/composer-caveat-v1/README.md).

The trace inspector now says “Decision schema validated”, preserving the distinction between parsing the decision and accepting its policy obligations. Raw events and the frozen controller/prompts/model remain unchanged. Final campaign ranks, prevalence and full 900 clean-checkout reproduction remain pending.
