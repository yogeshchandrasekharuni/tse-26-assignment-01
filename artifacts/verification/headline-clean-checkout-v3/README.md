# Successful full clean-checkout reproduction

`make clean-checkout` actually exited0. Its initially clean detached checkout used revision8eb6727d7236f7bce14c97fdf9f5f86fddea1121, with Python3.15.0/Fast Agent0.10.45 and completed dependency caches. Offline locked setup, deterministic data verification,106-test/frontend checks, framework playback and all900 comparison replays passed.

[The canonical result](../../../reports/data/clean-checkout.json) binds the five command logs in artifacts/verification/clean-20261015T133738Z. Full reproduction ended at2026-10-15T16:40:39.339681UTC; result copying completed2026-10-15T16:43:55.454590Z. [Matched comparisons](../../reproductions/20261015T135745Z/reproduction-comparison.json) and every generated artifact remain in the root evidence corpus. The clean script removed only its own successful temporary checkout.

The two earlier failed/stopped clean worktrees and their complete archives remain preserved in the v1/v2 packets. A reproduced natural violation remains a violation; this successful run does not imply that all MRs passed. The current runner uses bounded spawned process lifetimes and exact historical failed-seed attribution outside the unchanged frozen production/evaluation core.
