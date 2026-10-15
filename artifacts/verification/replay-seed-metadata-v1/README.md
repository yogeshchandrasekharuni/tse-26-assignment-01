# Replay-only metadata correction verification

The first complete clean-checkout playback failed strictly on failed-leg historical seed attribution. [The correction note](../../../REPLAY_METADATA.md) explains the exact scope. The original frozen runner, production service, statistical tools, comparator and live evidence have not changed.

The actual new regression command ran two tests in 32.62 seconds. These use a real four-decision natural failure and check its metadata plus auxiliary tampering/live-refusal controls. Full `make check` then exited0: **104 Python tests in218.97 seconds**, generated contract freshness, delivery lint/format/types, three frontend parser tests and frontend TypeScript/build/lint. [Complete log](make-check.log).

The adapter's manifest records revision `replay-failed-seed-attribution-1`, its source hash and per-leg unreachable-object collection policy. Successful corrected full900 reproduction must come from a fresh clean checkout; the focused regression and this check log cannot substitute for it.
