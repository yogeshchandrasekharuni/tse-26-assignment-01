# Completed MR03 live-evidence checkpoint

At 2026-10-05T15:42:17 UTC, `check.py` verified all 90 resolved MR03 comparisons: 30 distinct eligible bases, each with fixed seeds 104729, 130363 and 155921. All 90 attempts remain preserved, including output-contract violations. No resolved MR03 case is an infrastructure error.

The check validated strict case/request/output models, frozen-cohort and view bindings, requested/effective seeds, successful output/canonical hashes and failed terminal codes/stages. It verified 1,662 response cassettes across 180 referenced terminal physical captures, including failures. Cassette bytes match terminal inventories; internal semantic/response/order hashes verify. Offline Langfuse projection validation accepted all 180 captures without delivering observations or calling a model.

Those references comprise 104 new physical captures owned by MR03 and 76 explicitly reused successful source legs. Each reused record equals the referenced source outcome and is hash-bound. These are not 180 new MR03 runs. Referenced capture/cassette counts overlap earlier checkpoints and require physical-run deduplication before any combined summary.

`artifact-hashes.json` binds 10,705 files: all files beneath the ninety completed MR03 case directories plus referenced source records/captures. `checkpoint.json` binds that index, the frozen cohort, exact case paths, ownership, source-reuse lineage and preserved failure metadata. Frozen production/evaluation/configuration/data inputs have no diff from 8a50f75. `check.log` is the actual successful command output.

The separately bound `console-prefix.log` contains 10,523 bytes from the original runner through comparison 271 in MR04. `console-prefix.json` records its SHA-256, the 2026-10-05T15:48:18.634617Z copy time, observed progress and successful actual-secret-value scan. This preserves available console/retry history, not the final complete campaign console. Later output remains in the active temporary log and still requires final preservation.

Together with MR01 and MR02, this preserves **three of ten relations**. It does not calculate final rates/ranks, claim full 900-comparison completion, replace production playback, or claim current Langfuse dashboard delivery. Only completed MR03 folders are selected here; active MR04 files and mutable global progress remain with the runner.
