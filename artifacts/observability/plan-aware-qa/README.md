# Actual current plan-aware dashboard inspection

The local Docker dashboard displayed [the current MR05-b010/104729 follow-up](http://localhost:19300/project/housing-trajectories/traces/1c2251496736d8922db059a55c848eb4), with34 exact observed IDs acknowledged by actual readback. The copied receipt and projection are immutable QA snapshots; later working imports cannot rewrite them.

`repair-detail.jpg` shows event16 AGENT_REPAIR nested under Price/pass2 and generation008, with `recorded_iteration:0`, derived `iteration:1`, `iteration_label_basis:plan_and_invalid_decision` and the explicit raw-tag explanation. It also shows the later Supply generation and terminal failure. The raw source event remains unchanged.

`trajectory.jpg` shows event14's genuine refinement, changed strategy/specialist flags and equal before/after criteria hashes, alongside the real second-pass tree. The expanded view and saved DOM snapshots retain the full indexed→full_csv plan change and terminal `AGENT_POLICY_ERROR/SCANNING` message. No provisional aggregate is presented as a final result.

`inspection.json` binds the two required screenshots, current projection and actual acknowledgement only after these browser views were inspected. Pure offline `verify_plan_observability()` and the legacy evidence verifier subsequently exited0. This single-case proof does not substitute for the separately required whole-corpus readback inventory.
