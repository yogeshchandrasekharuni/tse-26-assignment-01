# A short professor demonstration

The story is a housing statistic, the decisions behind it, a changed plan, then the experiment that tests the complete system. All observations are synthetic. Recorded live calls and their offline playback are labeled separately. No fresh inference is needed for this walkthrough.

## Start the application

After the documented locked setup, run `make dev` and open <http://127.0.0.1:5173>. The API listens only on 127.0.0.1:8000 and the frontend on 5173. The initial Full synthetic feed example is a real saved live run, not a fabricated chart.

1. **A number with a trail.** In Explore, select a month and compare its chart detail with the monthly table. Switch USD to USD thousands or sq ft to m². The server changes display values; canonical statistics remain fixed. Open CSV or JSON to inspect exported values and provenance. Explain that price per area is the median of individual observation ratios.
2. **The sole public agent boundary.** Follow the agents to Workflow. The Orchestrator calls internal roles as tools; deterministic Python aggregation consumes their receipts. An absent Region event is shown as absent. Model decisions opens the actual inputs, responses and validation evidence.
3. **Natural feedback, unchanged criteria.** In Experiments choose headline-live-v1, Relation MR01, b010/seed104729, then the Source Inspect route. This is the report's natural sparse example: 16 model decisions, indexed to full_csv, diagnostic Region activated, REFINE then ACCEPT_LIMITED. Its 35 visible observations remain 35; the rescan confirms sparse support. The criteria hash stays fixed. It is not the injected index-omission control.
4. **An honest failure.** Choose MR05, b010/seed104729, then Inspect failed trace for the follow-up. The initial review refines; the second-pass Price purpose is invalid and the run ends with AGENT_POLICY_ERROR. Select event 16 Schema repair requested. The inspector shows pass 2 derived from the real plan and explains that the raw trace tagged pass 1. The original evidence is retained. No final result or unexecuted Composer call is invented.
5. **The complete experiment.** Experiments displays actual campaign completion and the resulting ten-row table when available. Each MR uses 30 distinct bases and the fixed three-seed panel. The primary unit is a base with any violation, with a nominal 95% Wilson interval. A violation is a finding; reproducing it correctly is successful playback. Source reuse and overlapping synthetic slices limit generalization. Open a paired case and its nonvacuity witness.
6. **Recompute, do not recite.** From Explore use Replay captured run. Playback feeds the recorded model decisions through current tools and control flow with network connections blocked. For the full reported table, `make reproduce` verifies and re-executes all 900 comparisons after setup and completed capture. The final clean-checkout proof is separate from this one-run UI example.

## Show the actual Langfuse trajectory

Once inference has finished, `make langfuse-up` starts the isolated local Docker project at <http://localhost:19300>. `make langfuse-export` imports completed campaign trajectories; it does not make new model calls. Preserve delivery attempts and require exact observation readback before claiming success. Existing local credentials are described in [the dashboard guide](observability/langfuse/README.md); keep the ignored environment file and its password off screen.

Use the guide's verified professor-demo links for ordinary completion, natural refinement and natural failure. The current plan-aware MR05 example additionally needs actual readback and browser inspection of its second-pass Price repair, as documented there. Raw captures remain canonical; the dashboard is their versioned readable projection. Interrupted prefixes retain their captured responses locally and do not receive fabricated terminal observations.

## Evidence to open alongside the demo

- [Design note](DESIGN_NOTE.md): parent boundary, cycles and why feedback changes work.
- [MR catalog](housing-tse-codex-handoff/MR_CATALOG.md): hypotheses, subdomains, exact/toleranced projections and witnesses.
- [Evidence index](EVIDENCE_INDEX.md): proof scope and current remaining work.
- [Runtime recovery](RUNTIME_RECOVERY.md): reboot, pinned runtime, retained mistakes and accounting.
- [Report sources](reports/README.md): editable manuscript, final evidence gates and PDF verification.

Do not call the assignment complete from a progress counter, a prepared dashboard payload or the marked working PDF. Final delivery requires the reviewed diagnosis, full clean-checkout playback, current dashboard readback/browser proof, complete UI/PDF inspection and submission checks.
