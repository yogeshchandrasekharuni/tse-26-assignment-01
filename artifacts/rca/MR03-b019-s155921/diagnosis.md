# Preliminary MR03 Supply-purpose failure

This is an observed role variant of the existing parent-purpose/pending-repair interaction. It is not a new distinct bug, final ranked case, new live sample or numerical replication counterexample. Both the fresh source and replicated follow-up failed; no successful source was reused and there is no complete canonical pair to compare.

The frozen MR03 input retains every original observation and adds one collision-free `replica-` record with every other field unchanged, including `listing_id`. The executed independent check examined all 34,560 original rows and 69,120 transformed rows. Raw integer predicates and calendar membership found 1,920 source and 3,840 follow-up visible observations, agreeing with the frozen witnesses. Exact view hashes bind the materialized bytes to the captured case. This check does not use the production selector, statistics or comparator.

The captured parent delegates in native order Price, Supply, Region and asks both Price and Supply for `purpose public_comparison`, which belongs to Region. Price returns its valid `statistics` purpose and produces a receipt at event5. Supply returns `public_comparison`; event6 rejects that literal, event7 opens its one repair, and scheduled Region then encounters the guard requiring the pending role repair to finish. The run terminates at event8 with `AGENT_POLICY_ERROR/SCANNING`. No aggregate or final output is published.

`PYTHONHASHSEED=0 .venv/bin/python scripts/replay_case_leg.py --case MR03-b019-s155921 --leg followup` matched all five recorded decisions, the failure code/stage and zero network attempts. Price executes afresh before that failure. Its result JSON and result hash match the live capture; raw receipt duration, run/receipt identifiers and paths differ. The existing natural Supply regression covers this same partial-receipt control path, so no duplicate regression or production change was added.

Evidence:

- [Strict playback comparison](20261005T094429Z/comparison.json) and [actual command output](replay.log).
- [Executed raw replication and boundary check](check_replication_boundary.py), [its output](boundary-check.log) and [hash-bound diagnostic](boundary-diagnostic.json).
- [Original complete case](../../campaigns/headline-live-v1/cases/MR03-b019-s155921/result.json), including both failed physical runs and every attempt.
- `integrity.json` binds the original case and this additional evidence packet. Full campaign rates, final case selection and 900-comparison clean-checkout playback remain pending.
