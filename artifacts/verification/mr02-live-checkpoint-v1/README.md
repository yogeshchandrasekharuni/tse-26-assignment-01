# Completed MR02 live-evidence checkpoint

At 2026-10-04T22:27:39 UTC, `check.py` verified all 90 resolved MR02 comparisons: 30 distinct eligible bases, each with fixed seeds 104729, 130363 and 155921. All 90 attempts remain preserved, including output-contract violations. No resolved MR02 case is an infrastructure error.

The check validated strict case/request/output models, frozen-cohort and view bindings, requested/effective seeds, successful output/canonical hashes and failed terminal codes/stages. It verified 1,692 response cassettes across 180 referenced terminal physical captures, including failures. Cassette bytes match terminal inventories; internal semantic/response/order hashes verify. Offline Langfuse projection validation accepted all 180 captures without delivering observations or calling a model.

Those 180 references comprise 104 new physical captures owned by MR02 and 76 successful source legs explicitly reused from MR01. The verifier binds each reused record to the exact source outcome and hashes its referenced capture. These are not 180 new MR02 model runs. Counts of referenced captures or cassettes across relation checkpoints must not be added without deduplicating physical run paths.

`artifact-hashes.json` binds 10,921 files: all files beneath the ninety completed MR02 case directories plus referenced source records/captures. `checkpoint.json` binds that index, the frozen cohort, exact case paths, run ownership, source-reuse lineage and preserved failure metadata. Frozen production/evaluation/configuration/data inputs have no diff from 8a50f75. `check.log` is the actual successful command output.

This completes preservation of **two of ten relations** when read with the MR01 checkpoint. It does not calculate final rates/ranks, claim full 900-comparison completion, replace production playback, or claim current Langfuse dashboard delivery. The main runner had advanced to 181/900 in MR03 during verification. Only completed MR02 case directories are selected here; mutable global progress and active MR03 files remain with the runner.
