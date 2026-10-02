# Preliminary natural failure: role-purpose contamination and pending repair

Recorded 25 September 2026. Campaign headline-live-v1 is still running; this is not a final top-three ranking or rate estimate. Case [MR01-b003-s155921](../../campaigns/headline-live-v1/cases/MR01-b003-s155921/result.json) is an eligible, completed **output-contract violation**, not a numerical median mismatch or infrastructure error.

The source completed. The row-permuted follow-up failed with `AGENT_POLICY_ERROR` at SCANNING after four genuine model decisions. The input-only frozen witness establishes the same selected membership under row permutation. The raw record order changes the dataset view identity, which enters the exact model context; equal numeric semantics do not imply identical model responses.

The first invalid decision is [model/002.response.json](../../campaigns/headline-live-v1/cases/MR01-b003-s155921/attempt-001/followup/runs/20261002T033100Z-17d9d8cdf3/model/002.response.json): Price returns `purpose: public_comparison`. Its strict schema permits only `statistics`. The preceding parent response explicitly tells Price to use `purpose public_comparison`, which belongs to Region. The raw invalid response is preserved before dispatch; no Price statistical receipt is accepted.

Trace events4-5 record the invalid Price field and one pending schema repair. A previously scheduled Supply child returns a valid statistics intent, but the global repair guard requires Price to finish first. Event6 records failure. The system correctly refuses to publish a successful result. Its reliability weakness is the combination of erroneous parent instruction, a child following it despite its role contract, and batched delegation that encounters another role before the repair can complete. This is an **agent/control interaction**, not evidence of corrupted listing data or wrong median arithmetic.

Competing explanations: the raw independent permutation witness rules out changed membership; there is no numeric comparison to blame on tolerance; the schema's distinct Price/Region purposes are explicit; no provider unavailability or tool crash is recorded. The harness follows its frozen rule that an eligible parse/policy fault counts as an output-contract violation. The evidence supports this particular first divergence, not a general frequency or sole cause for other future failures.

`PYTHONHASHSEED=0 .venv/bin/python scripts/replay_case_leg.py --case MR01-b003-s155921` actually ran. [Strict single-leg comparison](20261002T042749Z/comparison.json) matched the same four decisions, `AGENT_POLICY_ERROR`, failed terminal status and zero network attempts through actual Fast Agent playback and current tools/control. Replay does not add a sample. The focused integration regression copies only run-manifest, terminal and cassettes, removes saved final/numeric/trace outputs, and requires the same failed outcome.

The reduced JSON below isolates the first schema error. It is an extracted diagnostic fixture, not a newly executed live input or a substitute for the original captured context:

```json
{"role":"price","decision_type":"tool_intent","tool":"price_stats","partition_order":"month_asc","purpose":"public_comparison"}
```

A future revision could constrain parent child messages or schedule repair-aware delegation. Any such change must version the production boundary and rerun a new campaign; the running frozen campaign and this natural violation must remain unchanged. No patch, successful correction campaign, or pre/post-fix delta is claimed here.
