# Reboot recovery and frozen live runtime

The 6 October 2026 reboot stopped the campaign after 743 resolved comparisons. A read-only audit verified those case identities, 1,011 terminal physical captures, 59,380 saved files, prior checkpoint indexes and all 38 captured production input hashes. The original unfinished MR09-b008-s155921 follow-up retains six model responses and a seventh input without a response. Its raw bytes were not edited and it has no invented native terminal event.

The installed Ollama app returned version0.40.5 after reboot. The user explicitly approved stopping that idle app/server. Its installation and model files were retained. The official0.40.4 archive was downloaded into the ignored project cache and checked against GitHub's release-asset SHA-256 `a4ceae4b2aaf18df37ebcbfb56ba3a37a87838631112d66c2be07268693c8d58`.

## Metadata-order compatibility, revision1

The restored server reports the same seven model-default name/value pairs in different textual orders. Nine diagnostic requests matched every exact value; only three matched the frozen line order. The unchanged production guard compares the text literally. A separate local adapter now restores that order **only after exact parameter names and value strings agree**. Changed, missing or duplicate defaults fail closed. It does not modify inference request or response bytes, prompts, seeds, sampling settings, tools, contracts, dataset, cohort, comparisons or replay matching.

The verified0.40.4 backend listens on127.0.0.1:11435; the adapter occupies the original127.0.0.1:11434 endpoint. This is a versioned environment compatibility correction outside the frozen experiment implementation. Its code hashes, backend version, model digests and six successful invocations of the original production startup guard are recorded in [restored-provider.json](artifacts/verification/restart-recovery-v2/restored-provider.json). A labeled local fake-provider probe verifies changed-default rejection and unchanged chunked SSE/request bytes with zero real model calls. This extra transport hop and the reboot are additional reasons to treat runtime figures as descriptive.

Processes, when needed after verifying that the ports are free:

```sh
OLLAMA_HOST=127.0.0.1:11435 .cache/ollama/v0.40.4/runtime/ollama serve
.venv/bin/python -u scripts/serve_frozen_ollama.py
```

Run those as separate long-lived processes. The cache is not shipped or needed for offline playback; live recovery requires the verified binary and existing frozen model profiles. Do not silently use the newer installed app for this campaign.

## Preserved recovery mistakes and interruptions

The first recovery launch was incorrectly issued after its preflight failed. It was stopped. Two zero-decision MODEL_UNAVAILABLE startup failures and one additional interrupted attempt with four captured responses/five inputs remain in their original folders. They are recovery infrastructure history, not natural MR counterexamples. Explicit `interruption.json` postmortems bind both incomplete inventories and distinguish the user-reported reboot from the operator stop. Their timestamps record observation, not an invented restart instant.

Resumption uses the unchanged application service with the declared infrastructure-retry flag:

```sh
PYTHONHASHSEED=0 .venv/bin/python -u -m housing.evaluation run \
  --cohort configs/headline-cohort-v1.json \
  --directory artifacts/campaigns/headline-live-v1 \
  --retry-execution-errors
```

Completed pass/violation cases are retained. Recovery failures get new attempts. Provider-usage audit revision3 includes all saved responses from declared interruptions while leaving in-flight usage unknown. It still refuses an undeclared active capture. Completed-trajectory Langfuse export explicitly inventories interrupted captures instead of fabricating terminal events for them. Full current dashboard delivery remains pending.

## Durable progress and remaining work

The pre-reboot console in `/private/tmp/housing-headline-live-v1.log` was lost. Previously preserved console prefixes and the local watcher's history remain; the missing console is not reconstructed or claimed complete. The resumed console is durable:

```sh
tail -n 20 -f artifacts/verification/restart-recovery-v2/resumed-verified-campaign.log
```

The previous `/private/tmp` path is a convenience symlink to that log for this boot. The local watcher appends to `artifacts/verification/background-watch-v1/watch.log` and writes `ready.json` after the full campaign artifacts exist. It makes no Codex/model/network/Git calls while waiting; its final audits are local computations. `caffeinate` is bound to the resumed experiment PID, without persistent power-setting changes.

The first resumed pair was strictly replayed with matching canonical output. This recovery is not full900 reproduction or assignment completion. Reviewed diagnosis, current Langfuse readback/browser proof, full clean-checkout playback and final UI/PDF/submission checks remain required. MR violations are valid findings; completion does not require every MR to pass.
