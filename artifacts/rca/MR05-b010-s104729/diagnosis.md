# Preliminary failure after a genuine refinement

MR05-b010-s104729 has a completed source and a failed broadened-price follow-up. The independently checked input changes the inclusive band from USD200,000–450,000 to USD100,000–750,000, retaining all other request fields and the exact frozen CSV. Raw integer/calendar predicates find27 source and35 follow-up visible observations. Every source record remains selected in its month, with a strict expansion in at least one month, agreeing with the frozen nonvacuity witness. The missing final follow-up output prevents a numerical MR comparison; the eligible outcome is an output-contract violation.

Both legs genuinely refine. In the follow-up, Price and Supply first complete their exact tools and event8 aggregates their receipts provisionally. Reviewer requests refinement at10. The parent changes indexed scanning to full CSV and activates diagnostic Region, with identical before/after canonical query hashes. Event14 records the real plan change. Parent response007 then schedules Price, Supply and Region in that order and incorrectly asks Price and Supply for `coverage_diagnostic purpose`, which belongs to Region. Price response008 copies that purpose; event15 rejects it. Event16 opens its one repair. Scheduled Supply response009 is model-generated, but the pending-Price-repair guard prevents it from becoming an accepted role decision. Event17 terminates with `AGENT_POLICY_ERROR/SCANNING`. No second-pass tool, second aggregate or final output is accepted.

This is another context for the known parent-purpose/batch/pending-repair interaction, not a new distinct bug, final ranking or numerical price-band counterexample. In particular, an initial provisional aggregate cannot substitute for completion after a requested refinement.

`PYTHONHASHSEED=0 .venv/bin/python scripts/replay_case_leg.py --case MR05-b010-s104729 --leg followup` matched all ten recorded decisions and the same failure, with zero network attempts. Both initial statistical tools execute afresh; their result JSON and result hashes match the live records. Receipt duration, identifiers and evidence paths differ as expected. The new minimal-capture integration regression supplies only manifest, terminal and cassettes, removing saved results, receipts, traces and final outputs before playback.

Inspection exposed a separate trace-label defect: the frozen repair emitter defaults to iteration0, although the active plan and immediately preceding invalid Price decision both record iteration1. The raw capture and frozen controller remain untouched. A conservative read-side annotation requires those two witnesses and the same actor; the API retains raw `iteration` while adding `display_iteration` and its basis. The UI identifies the derived pass and explains the raw tag. A versioned Langfuse projection also reattaches the repair to the proven second-pass Price generation, with distinct trace and observation IDs. The older exporter and its delivered evidence remain unchanged. This new projection is prepared and tested offline only; actual dashboard delivery/readback/browser verification remains pending while Docker is stopped for inference memory.

Evidence:

- [Strict playback comparison](20261006T180443Z/comparison.json) and [actual command output](replay.log).
- [Executed raw-input/control-flow check](check_refinement_boundary.py), [output](boundary-check.log) and [bound diagnostic](boundary-diagnostic.json).
- [Plan-aware offline projection](plan-projection.json), preserving the recorded event input and explicit annotation.
- [Desktop/mobile annotation proof and checks](../../verification/trace-iteration-v2/README.md).
- [Original complete case](../../campaigns/headline-live-v1/cases/MR05-b010-s104729/result.json), including the successful source, failed follow-up and every attempt.

The integrity packet binds the original case and this diagnostic. Full campaign results, final case selection, complete clean-checkout playback and new dashboard readback are still pending.
