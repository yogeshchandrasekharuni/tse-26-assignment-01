# Reviewed top-three relation diagnosis

The complete primary base-level ranking selects **MR03, MR05 and MR07**. The selection is made from all ten complete rows, using descending exact rate, descending violating-base count and ascending MR identifier. Representatives are the first lexicographic violating case per selected relation. These three relations share the same demonstrated representative mechanism; this packet does not invent three independent bugs or claim a cause for all 210 violating pairs.

Actual executed command:

```sh
PYTHONHASHSEED=0 .venv/bin/python -u artifacts/verification/headline-rca-v1/check.py
```

The preserved [command log](check.log) records all three successful checks. The checker independently applies integer raw-CSV predicates, validates the transformation witnesses, examines actual parent/Price/Supply responses, and executes the production Fast Agent playback from a reduced persisted capture. The [review](review.json) binds original evidence and regenerated playback files.

| Relation and selected leg | Independent witness | Actual replay |
| --- | --- | --- |
| MR03-b001-s104729 follow-up | Unique-record twofold replication; selected 2,880 → 5,760 | Four decisions, same policy failure, zero network |
| MR05-b001-s104729 source | Proper widening inclusion, 2,149 → 2,880; failure occurs before transformation | Four decisions, same policy failure, zero network |
| MR07-b001-s130363 follow-up | Eleven identical overlap multisets; 240 observations enter and leave | Four decisions, same policy failure, zero network |

The parent queues Price, Supply and Region and sends the Region-only `public_comparison` purpose to Price. Price copies it; its schema requires `statistics`. A repair request becomes pending. Supply still makes a real model call and returns schema-valid JSON; the controller rejects accepting it because Price repair is unfinished. The run fails at SCANNING with no numeric tool, aggregate or final output. This is an eligible output-contract violation. It is not an observed numerical relation counterexample.

The reduced captures contain only `run-manifest.json`, `terminal.json` and four original cassettes. They omit source model files, traces, tool results, receipts and outputs. The complete dataset, exact semantic identities and model-response panel remain fixed; this is a reduction of replay dependencies, not a claim of a smallest statistical input or a newly sampled model response. Each case can also be replayed individually with `scripts/replay_case_leg.py` and its recorded leg.

Raw-boundary JSON files show an auxiliary constructed Price decision with only its purpose corrected. That local schema control is explicitly not a real model response, deployed behavioral fix or empirical rerun. Future role-specific messages and queue-aware repair need a separately versioned evaluation. Other naturally observed mechanisms, including Reviewer schema echo and Composer caveat omission, retain their own earlier diagnostics and are not recast as these selected cases.

`summarize.py` validates all review hashes and writes [the final report diagnosis](../../../reports/data/diagnosis.json), including alternatives, limitations and evidence bindings. The original corpus remains unchanged.
