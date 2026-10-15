# Housing Evidence

An exact, inspectable multi-agent housing-trends application for the IIIT Hyderabad TSE assignment. The data is **synthetic**, generated locally and frozen; it does not measure the Dallas housing market.

Current verified milestone: the complete live campaign is captured and audited: **10 relations × 30 bases × 3 paired seeds = 900 comparisons**. All **690 pairs with both canonical outputs** satisfy their declared numerical projections; **210 pairs have eligible output-contract violations**, which remain genuine findings. Each MR has thirty completed bases and no unresolved infrastructure errors. The corpus retains historical startup failures and two interrupted captures. Ranked diagnosis, complete-result desktop/mobile checks and current plan-aware Langfuse browser proof are verified. Full corrected clean-checkout playback, whole-corpus dashboard readback and the final twelve-page report remain pending.

## Run locally

Requirements: current uv, Node 26.5.0/npm, and the completed locked Python/frontend setup. Python 3.15.0 and Fast Agent 0.10.45 are pinned. On the original workspace a local uv 0.13.1 is available under .cache/uv-bootstrap; a fresh checkout uses an installed current uv.

```sh
make setup               # locked Python environment and npm ci; downloads allowed here
make data                # two independent regenerations; verify frozen bytes/provenance
make check               # Python lint/format/types/tests, schema/type freshness, frontend parser tests/build/lint
make dev                 # local API on 8000 and React on 5173; Ctrl-C stops the owned processes
```

Open http://127.0.0.1:5173. The initial screen displays a labeled genuine live capture. “Replay captured run” executes current tools/control flow through Fast Agent PlaybackLLM with sockets denied. It needs no Ollama model or API key. “Run live analysis” uses the local verified model profiles described below.

The recorded-example selector also includes “No matching observations”: a genuine auxiliary live run whose price bound exceeds every frozen observation. It preserves all twelve empty months, unavailable statistics and the actual review/rescan trace. Its capture and strict offline playback are excluded from headline experiment counts.

A short [professor demonstration](DEMONSTRATION.md) follows the numbers, the real feedback loop and a preserved natural failure.

Explore links monthly chart selection to a tabular record, with backend unit conversion and CSV/JSON export. Workflow exposes parent/child topology, the actual feedback cycle, causal events, exact model inputs/responses and dispatcher results. Experiments exposes recorded campaign progress, base-level summaries, paired cases, witnesses and failure evidence. Provenance explains the frozen source and statistical contract.

The required [local Langfuse demonstration dashboard](observability/langfuse/README.md) imports the real recorded trajectories through OTLP. `make langfuse-up` starts its isolated Docker project on localhost19300; `make langfuse-watch` observes completed campaign and interactive live runs. It preserves failed calls and feedback links, verifies observation readback, and keeps the running experiment's frozen inputs unchanged. Langfuse is not needed for offline analysis reproduction or `make check`.

## Agent boundary and statistics

The **Orchestrator is the sole public agentic entry and exit**. Fast Agent registers it with `@fast.agent(name="orchestrator", agents=[...])`. Price, Supply, conditional Region, Coverage Reviewer and Composer are internal agents as tools. This differs from Fast Agent's native `@fast.orchestrator` planner; the choice is supported by installed-source inspection and live probes in [FRAMEWORK_FINDINGS.md](FRAMEWORK_FINDINGS.md).

Every child performs a real model call and returns a role-specific JSON decision. Trusted Python binds immutable arguments, executes exact tools and validates receipts. Aggregation consumes the specialist receipts. Reviewer feedback changes indexed→full_csv, can activate Region, and can request one further distinct rebuilt-index strategy for a new integrity signal. User criteria never change. Composer selects grounded facts; the parent submits a typed terminal decision and returns the verified acknowledgement before successful output is published.

Counts are monthly observation records. Repeated business listing labels are retained; duplicate record IDs invalidate a dataset. Monthly medians, individual price/size-ratio medians, percentages and pooled ZIP ranks use integers/Fraction internally. Canonical values serialize once with six-decimal half-even rounding. Null never means zero. The browser receives generated strict domain types and backend-produced display values/chart geometry.

The shared entrypoint is [run_analysis](src/housing/workflow/service.py), used by CLI, API and evaluation. Each run has isolated context, bounded repairs/refinements/retries, conservative pre-inference context checks, raw model decisions, trusted receipts and append-only trace evidence. Output-contract failures stay failures; infrastructure errors leave experiment bases incomplete.

The trace inspector preserves raw iteration tags and identifies any pass label derived from the active plan and preceding invalid decision. Its JSONL export remains byte-identical to the capture. A real [failure after refinement](artifacts/rca/MR05-b010-s104729/diagnosis.md) exercises that annotation and proves that an earlier provisional aggregate cannot become a final answer after the later pass fails.

## Frozen source and runtime

- Dataset: **34,560** observations, **24** months (October 2024–September 2026), twelve ZIPs, 1,440 repeated listing labels. [Manifest](data/manifests/dallas-synth-v1.json).
- CSV SHA-256: `bb0e9f3ed47a65eabbaab4e0a4de192ca7918a61eee111e273a70e145f87692b`.
- Python **3.15.0** / fast-agent-mcp **0.10.45**, exactly resolved in uv.lock.
- Local Ollama **0.40.4**, Qwen3.5 9B Q4_K_M. Current profiles: `housing-qwen-v4-s104729`, `housing-qwen-v4-s130363`, `housing-qwen-v4-s155921`; context 65,536 and completion 1,024. Full digests/defaults: [model manifest v4](configs/model_manifest_v4.json).
- Live inference uses 127.0.0.1:11434, a local dummy key `ollama`, reasoning_effort none and verified per-model seed defaults. SDK retries are disabled; one framework transport retry is allowed. Fixed seeds remain best-effort control conditions.
- Frontend resolves React **19.3.1**, Vite **8.3.4**, TypeScript **6.0.3**, self-hosted Public Sans and Lucide icons; npm's full resolution is locked.

Live commands require those existing local profiles. Offline reproduction requires completed setup and captured evidence, and never downloads or starts a model. Historical profile manifests and failed probes are retained separately.

After the 6 October 2026 reboot, the campaign was recovered from743 saved comparisons using the pinned0.40.4 binary and a strict metadata-order adapter at the same endpoint. See [runtime recovery](RUNTIME_RECOVERY.md) for commands, preserved interruptions, the durable progress log and the disclosed temporary-console loss. Frozen production/evaluation inputs remain unchanged.

Offline setup may reuse completed caches with `UV_CACHE_DIR` and `UV_PYTHON_INSTALL_DIR`; Makefile defaults stay inside the checkout and honor explicit environment overrides. The clean-checkout verifier also sets uv/npm offline mode. Font/icon/runtime dependency notices ship under frontend/public/licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).

## Experiments and reproduction

The ten relations and their subdomains/projections are in the preserved [MR catalog](housing-tse-codex-handoff/MR_CATALOG.md). [EVALUATION_NOTES.md](EVALUATION_NOTES.md) records versioned implementation choices: independent raw-CSV eligibility, sparse coverage revision, exact tolerances, Decimal Wilson endpoints and source-reuse lineage.

[The frozen headline cohort](configs/headline-cohort-v1.json) has thirty distinct eligible bases per MR and all three paired seeds 104729/130363/155921. All 300 MR/base inputs passed independent preflight before headline outcomes. It includes empty/sparse/dense months and odd/even cardinalities. The workload is deliberately designed, overlapping and synthetic; it is not a random sample of cities or users.

```sh
make evaluate-live       # run/resume frozen live work; verify a completed capture without changing it
make reproduce-pilot     # verify pilot artifact hashes and rerun all 9 comparisons offline
make reproduce           # same workflow for all 900 headline comparisons once capture is complete
make report-draft        # marked twelve-page working PDF, no invented headline numbers
make clean-checkout      # after commit/completion: offline setup/checks/full reproduction in a detached checkout
make report              # final PDF; requires complete results, diagnosis and clean-checkout evidence
make submission-check    # checks plus strict evidence/PDF consistency gates
```

`make evaluate-live` now verifies all identities and artifact bytes when the campaign is already complete, then returns without new inference or finish-metadata changes. Only run a resume command after checking that the original runner has stopped. The historical direct module command in RUNTIME_RECOVERY.md records the actual recovery invocation; use the guarded Make target for ordinary entry.

The primary outcome is **a base with any violation among its three paired seeds**. Wilson intervals use completed bases, never 90 correlated seed runs. A model parse/policy/output-contract fault on an eligible input is a violation; model/tool/process infrastructure failures remain execution errors. Every attempt, invalid candidate, failure and source reuse is visible. Each follow-up executes afresh.

Replay reads captured model responses, restores native call order, matches exact prompt/schema/tool/data/model/seed/upstream receipt identities, and re-enters the current Fast Agent workflow. It never loads saved final outputs to execute an analysis. Integration tests replay with source outputs/receipts/results/trace removed; a changed current receipt fails before the next captured response. A reproduced natural violation is successful reproduction; completion does not require zero violations.

The first full clean-checkout run executed all900 but correctly rejected failed-leg seed bookkeeping. A [versioned replay-only attribution adapter](REPLAY_METADATA.md) repairs that metadata only after complete exact playback, preserves the uncorrected record, and leaves frozen live/evaluation code unchanged. The current replay driver bounds interpreter lifetime to sixteen physical analyses per local process; the earlier costly per-leg-GC rehearsal is preserved too. The failed full run is preserved; a successful corrected full run is still required.

Full reproduction, final report, clean-checkout and submission checks intentionally reject incomplete headline evidence. Their completion guards have been exercised; a full successful run still depends on the executing campaign. Editable report prose and primary references are in [reports](reports/README.md). No draft is a submission-ready claim.

CLI examples:

```sh
.venv/bin/python -m housing.cli analyze --request configs/example-request.json
.venv/bin/python -m housing.cli analyze --request configs/sparse-request.json --inject-index-omission
.venv/bin/python -m housing.cli analyze --request configs/example-request.json \
  --mode replay --capture artifacts/traces/20261001T150456Z-6c0cbee2b9
```

The index-omission command is an explicitly labeled auxiliary control. It preserves CSV bytes, changes the index, triggers actual review/refinement and recovers2→3 observations. Its current live/replay captures made sixteen decisions. It is excluded from headline denominators. `make probe-*` commands retain the separate earlier environment proof; those probes are not housing MR outcomes.

## Evidence and development

- [Pilot live](artifacts/campaigns/pilot-live-v1/headline.json) and [pilot replay match](artifacts/campaigns/pilot-replay-v1/reproduction-comparison.json): three bases, nine comparisons, eighteen physical analyses, 210 model decisions, six natural sparse refinements, zero schema repairs. These numbers describe the pilot only.
- [Pilot provider audit](reports/data/pilot-provider-usage.json): actual usage/retry channels from unique physical live runs. Replay usage is historical, not new inference; null fields remain unavailable.
- [Clean-checkout pilot verification](reports/data/pilot-clean-checkout.json): revision f7c11d6, initially clean; offline setup, data regeneration,72 tests, frontend checks, framework playback and nine recomputed pilot pairs passed. Its scope is explicitly pilot and cannot satisfy final headline gates. Run the same rehearsal with `.venv/bin/python scripts/clean_checkout.py --pilot`.
- [First natural failure diagnosis](artifacts/rca/MR01-b003-s155921/diagnosis.md) and strict single-leg replay: preliminary evidence, not a final ranking or rate. `scripts/replay_case_leg.py --case MR01-b003-s155921` recomputes its failure through the shared service.
- [Architecture/design note](DESIGN_NOTE.md), [visual system](DESIGN.md), and [finish verdict](.impeccable/review/finish-verdict.md): the reviewer scored all three named fixes resolved across replacement desktop/mobile/user-width captures.
- [NOTEBOOK.md](NOTEBOOK.md): actual commands, timestamps, versions, failures, corrections and remaining work.
- [AI_USE.md](AI_USE.md): the AI-generated handoff and substantive AI implementation/design work, errors and how execution caught them.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), [DECISIONS.md](DECISIONS.md): scope, gates and user overrides.
- `make contracts`: regenerate JSON Schema, OpenAPI and TypeScript from strict Python boundary models. `make check` rejects stale generated contracts.
- Original assignment, source diagrams and AI handoff are preserved in housing-tse-codex-handoff/. The assignment governs coursework requirements; explicit user overrides supersede handoff defaults.

The assignment lists **25 September 2026**, teams of **two**. No submission hour or author identities are inferred. No paid API, personal listing data, scraping, public deployment or external messaging is used.
