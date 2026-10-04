# Preliminary MR02 diagnosis: a shared purpose/repair mechanism

This is the first saved MR02 violation, inspected while headline-live-v1 is still running. It is not a final top-three selection, prevalence estimate or numerical counterexample. The eligible pair is an output-contract violation under the frozen protocol.

MR02 changes nominal record/listing identities through bijections. An independent CSV check examined all34,560 source/follow-up row pairs: every nonidentity field is unchanged; all34,560 record identities and1,440 business-listing identities map one-to-one, preserving listing equality classes. Both raw visible slices contain2,880 observations,240 in each month from July2025 through June2026. These are independently recomputed input witnesses, not a missing follow-up statistical result. See [boundary-diagnostic.json](boundary-diagnostic.json) and the executed [check](check_boundary.py).

The source was a successful exact-identity reuse of [MR01-b001-s104729/source](../../campaigns/headline-live-v1/cases/MR01-b001-s104729/attempt-001/source/record.json). The current case records that lineage explicitly. The follow-up made four genuine model decisions and failed at SCANNING:

1. Parent response001 schedules Price, Supply and Region in that preserved native order. Its Price message explicitly requests `purpose public_comparison`, which belongs to Region.
2. Price response002 is valid JSON syntax but contains that invalid purpose. Trace event4 rejects it: Price requires `statistics`. No statistical receipt is accepted.
3. Event5 marks one pending Price schema repair. Already scheduled Supply response003 contains a valid statistics intent, but reaches the global guard while Price still owns the repair. Event6 ends with AGENT_POLICY_ERROR. The parent has not received a turn in which to repair Price before the rest of its batch executes.

This is the same observed agent/control interaction diagnosed in [MR01-b003-s155921](../MR01-b003-s155921/diagnosis.md), under a different transformation. It is not evidence of a second independent bug or an arithmetic/identity-deduplication fault. The raw bijection/field checks support the relation's input conditions. No numerical MR comparison ran, and the output-contract classification follows the declared rule. The changed data-view identity enters the model context; this pair does not isolate the causal effect of relabeling from model/control behavior or the successful-source reuse policy.

The actual command `PYTHONHASHSEED=0 .venv/bin/python scripts/replay_case_leg.py --case MR02-b001-s104729 --leg followup` reproduced the same four-decision failure through current production Fast Agent playback, with no network attempts. [Comparison](20261004T054210Z/comparison.json) and recomputed trace remain preserved. This replay is not a new live sample. The reduced invalid-intent fixture already documented for MR01 isolates the same schema field; it is additional diagnostic evidence rather than a substitute for this exact context.

Prospective changes include constraining parent role instructions or deferring remaining batch children while a repair is pending. They require a separately versioned implementation and new campaign. No mitigation, successful correction run or pre/post improvement is claimed here; the frozen execution remains unchanged.
