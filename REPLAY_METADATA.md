# Failed-playback seed attribution, revision 1

The first full clean-checkout reproduction at revision `90d27b7a4ad2aee29059611e00ee8583bd811e76` executed all 900 comparisons and then failed strict semantic comparison. All 210 contract-violating cases differed only in failed-leg `effective_seed`: live records held the historical profile seed, while playback records held null. The other compared semantic fields matched. This was a reproduction bookkeeping fault, not an additional natural model finding or a changed headline outcome.

The frozen runner fills a failed leg's seed only when that new run contains captured cassettes. Live execution writes cassettes; playback deliberately consumes the original cassettes and writes no new capture. Consequently, correctly reproduced failures lost their seed attribution. The first aggregate rejected this mismatch rather than silently ignoring the field. Its logs, all 900 generated cases and diagnostic are preserved under `artifacts/verification/headline-clean-checkout-v1` and the retained failed worktree.

`src/housing/reporting/replay_metadata.py` adds a versioned **replay-only** adapter. The production service, Fast Agent playback, frozen runner, comparator, statistical calculations, prompts, seeds and original campaign bytes remain unchanged. `scripts/reproduce_campaign.py` uses the adapter; its revision and source hash are recorded in each new reproduction manifest.

After the original runner actually executes a failed leg, attribution requires:

- A declared contract failure, matching failed status/code/stage in live and replay terminals.
- Identical current/live/replay full execution identities and boundary hashes, including seed, model, prompt, schema, tools and dataset.
- The entire nonempty original cassette inventory, unchanged bytes and the same number of actually replayed decisions.
- No network attempts, no new replay cassettes and an exact original leg record.

Only then can `effective_seed` carry the historical profile seed. It does not claim a fresh provider sample, stronger hardware determinism or proof that a provider honored a seed. An explicit `seed-attribution.json` binds the evidence, and `record.before-seed-attribution.json` preserves the original null-valued leg record. The raw playback trace, decisions, receipts, tools and outcome are not changed. Replay misses and infrastructure failures cannot acquire attribution.

The failed process also retained a 30.9 GB heap during Python module finalization. A one-second macOS stack sample showed `_Py_Finalize → finalize_modules → gc_collect_main`, after the final comparison exception. Only that verified owned child was terminated; its files remain preserved. The new replay adapter calls `gc.collect()` after each physical playback leg to reclaim unreachable per-run objects promptly. This is a replay resource policy, recorded in its manifest, with no live or model configuration change.

Two regression tests exercise an actual four-decision natural failure without saved outputs, exact historical attribution, preserved uncorrected metadata, mismatched seed, incomplete sequence, blocked-network evidence, replay miss and refusal of live execution. The full corrected clean-checkout reproduction is a separate run; this document alone does not claim it passed. Final proof belongs in `reports/data/clean-checkout.json` and its bound command logs.
