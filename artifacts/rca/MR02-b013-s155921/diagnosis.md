# Preliminary Supply-purpose variant: partial work is not a result

This eligible MR02 pair is an output-contract violation. Both its fresh source and follow-up failed with AGENT_POLICY_ERROR at SCANNING; no source reuse or completed numeric pair is claimed. This packet focuses on the follow-up. It is not a final ranked case, a new statistical sample or evidence of a separate underlying bug.

The follow-up's preserved native batch is Price, Supply, then Region. Parent response001 requests `purpose public_comparison` from both Price and Supply. That purpose belongs to Region; Price and Supply require `statistics`. Their actual responses differ:

- Price response002 returns `statistics` despite the parent message. The current Price tool executes and its receipt is accepted at trace event5.
- Supply response003 returns `public_comparison`. Event6 records the role-specific literal error; event7 marks one pending Supply repair.
- Scheduled Region response004 reaches the global guard while Supply still owns the repair. Event8 ends the run. No aggregate, review or final result is published.

This extends the already observed [purpose/pending-repair interaction](../MR02-b001-s104729/diagnosis.md) to a later child after partial valid work. It shows why a table of schema-error locations cannot, by itself, count distinct root causes. The frozen MR02 preflight marks this input eligible; exact playback reconstructs its recorded transformed-view identity. There is no numeric MR comparison to blame on arithmetic or tolerance.

The actual command `PYTHONHASHSEED=0 .venv/bin/python scripts/replay_case_leg.py --case MR02-b013-s155921 --leg followup` matched all five decisions and the failed terminal with zero network attempts. [Comparison](20261004T121917Z/comparison.json) and the recomputed Price result/receipt are retained. The Price result matches the recorded JSON exactly and has the same result hash. Fresh raw receipt IDs, run IDs, paths and duration differ, as recorded in [boundary-diagnostic.json](boundary-diagnostic.json); no whole-receipt equality is claimed.

The [minimal-capture regression](../../../tests/integration/test_failure_playback.py) supplies only run-manifest, terminal and cassettes, with no saved output, tool result, receipt or trace. Current production tools freshly create the Price result and receipt before the same Supply error. It requires five decisions, zero network attempts, no AGGREGATE_COMPLETED event and no final output. The earlier Price-first and Reviewer-repair regressions remain covered.

All three focused natural-failure cases passed in4.69seconds. Full make check subsequently passed75 Python tests in21.63seconds, three frontend tests and lint/types/schema/build checks. Actual logs are under artifacts/verification/partial-receipt-regression-v1. Initial lint caught two unparenthesized implicit string concatenations in the parameter tuples; the before log is retained and corrected formatting passed the full check. These are test/evidence changes outside the frozen production/evaluation boundary. No mitigation campaign or pre/post improvement is claimed.
