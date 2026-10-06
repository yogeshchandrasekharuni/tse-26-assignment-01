# Completed MR04 live-evidence checkpoint

At 2026-10-06T08:07:27 UTC, `check.py` verified all 90 resolved MR04 comparisons: 30 distinct eligible bases, each with fixed seeds 104729, 130363 and 155921. All 90 attempts remain preserved, including output-contract violations. No resolved MR04 case is an infrastructure error.

The check validated strict case/request/output models, frozen-cohort and view bindings, requested/effective seeds, successful output/canonical hashes and failed terminal codes/stages. It verified 1,690 response cassettes across 180 referenced terminal physical captures, including failures. Cassette bytes match terminal inventories; internal semantic/response/order hashes verify. Offline Langfuse projection validation accepted all 180 captures without delivering observations or calling a model.

Those references comprise 104 new physical captures owned by MR04 and 76 explicitly reused successful source legs. Each reused record equals the referenced source outcome and is hash-bound. These are not 180 new MR04 runs. Referenced capture/cassette counts overlap earlier checkpoints and require physical-run deduplication before any combined summary.

`artifact-hashes.json` binds 10,904 files: all files beneath the ninety completed MR04 case directories plus referenced source records/captures. `checkpoint.json` binds that index, the frozen cohort, exact case paths, ownership, source-reuse lineage and preserved failure metadata. Frozen production/evaluation/configuration/data inputs have no diff from 8a50f75. `check.log` is the actual successful command output.

The separately bound `console-prefix.log` contains 13,886 bytes from the original runner through comparison 360. `console-prefix.json` records its SHA-256, the 2026-10-06T08:13:28.333570Z copy time, observed progress and successful actual-secret-value scan. This preserves available console/retry history, not the final complete campaign console. Later output remains in the active temporary log and still requires final preservation.

Together with MR01–MR03, this preserves **four of ten relations**. It does not calculate final rates/ranks, claim full 900-comparison completion, replace production playback, or claim current Langfuse dashboard delivery. Only completed MR04 folders are selected here; active MR05 files and mutable global progress remain with the runner.
