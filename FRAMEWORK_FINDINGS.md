# Fast Agent environment proof and orchestration choice

Reviewed 25 September 2026. This is an environment/integration spike, not a housing application or a headline experiment. All example observations below come from the explicitly synthetic 48-row handoff fixture. The feedback demonstration intentionally omits March 2026 from the index only.

## Choice

Use **agents as tools**: a parent `@fast.agent(name="orchestrator", agents=[...])` with Price, Supply, conditional Region, Reviewer and Composer as children. The parent Orchestrator is the only agent called by the application and the only agent returning to it. Each child result returns to that parent. Deterministic aggregation is a typed Python tool, not a seventh model agent.

This matches the user's intended topology. It also gives the parent access to deterministic local tools alongside child-agent tools, without requiring an unconstrained planning/synthesis workflow to own the public numerical output.

## Documentation and installed-code comparison

Primary documentation:

- [Workflows: Orchestrator](https://fast-agent.ai/agents/workflows/#orchestrator)
- [Workflows: Agents As Tools](https://fast-agent.ai/agents/workflows/#agents-as-tools)
- [Python API](https://fast-agent.ai/agents/defining/python_api/)
- [Model overlays](https://fast-agent.ai/models/model_overlays/)
- [Internal playback models](https://fast-agent.ai/models/internal_models/)
- [Ollama OpenAI-compatible API](https://docs.ollama.com/api/openai-compatibility)

| Concern | `@fast.orchestrator` | `@fast.agent(agents=[...])` |
|---|---|---|
| Delegation | Model generates structured planning steps; framework executes assigned tasks | Parent model calls children as tools named `agent__price`, etc. |
| Dependent work | Tasks inside one planning step run concurrently; prerequisites need separate steps | Parent can wait for a child result before issuing the next call; tool guards still enforce order |
| Final return | Built-in planner performs an additional synthesis step | Parent returns its own final response after receiving child results |
| Deterministic tools at parent | Orchestrator decorator has no `function_tools`/MCP server parameters in the inspected version | Parent supports local typed function tools and MCP tools alongside children |
| Histories | Children are registered agents; use_history configuration controls retained history | Detached child instances; explicit `history_source="none"`, `history_merge_target="none"` avoid inheritance/merging |
| Bounds | `plan_iterations` counts planning steps | `max_iterations` bounds tool-loop rounds; separate application guard bounds semantic refinements |
| Suitability here | Feasible, but requires particular care with dependency steps and final output | Preferred for the intended parent/child topology and explicit tool/action boundaries |

Installed Fast Agent 0.10.45 facts, read from the locked distribution:

- `core/direct_factory.py::_create_planner_agent` creates `IterativePlanner` for the native orchestrator registration. Both native orchestration decorators map to that implementation.
- `agents/workflow/iterative_planner.py` accepts but discards the `plan_type` constructor argument. Do not assume selecting `full` gives a distinct implementation in this installed release.
- That planner groups different agents' tasks in a step and runs them with `asyncio.gather`; it then generates a final synthesis with a built-in Markdown-oriented prompt.
- `agents/workflow/agents_as_tools_agent.py` exposes children through `agent__<name>` tools, creates detached child instances, and implements the configured history and concurrency options.
- These findings are version-specific. They are not a claim that the native planner is universally unsuitable or that agents as tools is automatically reliable.

## What actually ran

### Seeded decisions and isolation

Fast Agent named `.send()` calls returned strict JSON for each seed 104729, 130363 and 155921. A transparent localhost proxy saved actual request bodies and responses. Requests selected the expected derived Ollama model names and contained `reasoning_effort: none`, with no conflicting seed override. Resolved model defaults were independently inspected through Ollama.

The same role's follow-up request and a second role's request did not contain the source-only marker or prior user messages. Profile selection/default seeds are verified; inference repeatability remains best effort, not a claim of deterministic hardware kernels or statistically independent seeds.

### Native planner attempt

Evidence: `artifacts/framework_probe/20260930T175521Z-all-ad789e/`.

The planner initially scheduled Reviewer in the same concurrent step as its prerequisite Price and Supply scans. The policy check rejected the early review. The planner subsequently recovered, and the real Reviewer requested REFINE. Price/Supply switched from indexed to full CSV, Region ran, Reviewer accepted limited support, and Composer's real tool generated the 24-observation report.

The final native response summarized workflow steps and receipt IDs instead of returning that verified observation count/report. The probe's final-return assertion failed. Its full status remains **failed**, despite the successful tool/feedback substeps. This is an integration/output-boundary finding from one probe, not an MR violation or a general framework benchmark.

### Agents-as-tools attempts

The first attempt, `20260930T184341Z-agents-tools-0d8bfa`, exposed a registration mistake: bound methods carried an evidence writer containing a thread lock, and detached-child configuration copying failed with `cannot pickle '_thread.lock' object`. Changing the model's message cannot fix that error. The attempt was stopped and preserved.

The corrected attempt, `20260930T185306Z-agents-tools-cda931`, registered plain typed closures bound to that run's tool service. It passed:

1. Price and Supply executed indexed scans: 22 selected visible observations; omitted month count 0.
2. The real Reviewer called its review tool with REFINE / EXACT_RESCAN_WITH_REGION.
3. The plan changed to full_csv and active specialists changed from Price/Supply to Price/Supply/Region.
4. All three real specialist tools ran; full scan selected 24 observations and restored omitted month count 2.
5. Reviewer chose ACCEPT_LIMITED for genuine remaining sparsity.
6. Composer selected grounded facts; the parent Orchestrator returned a response carrying 24 observations and the sparse-support caveat.

The query hash remained `25f16ca91607f33ea413b4e1d73d9ec78e03b7d4d83aac1651ff17911812f8a5`. It made 24 provider requests and took about 1298.00 seconds on this fixture. This single instrumented run is not a throughput benchmark or a forecast for the full campaign.

### Strict offline playback

Three actual captured JSON decisions were passed through Fast Agent playback in fresh contexts, then dispatched to the current Python tool. Exact request/schema/tool/fixture mismatches were rejected; no saved analysis output supplied the arithmetic. Network connection functions were blocked inside the replay process.

A further native-tool-call probe passed in `20260930T193332Z-tool-playback-d83da3/`: playback returned a captured assistant tool call, Fast Agent executed the current Python tool, and the recorded final decision was consumed only after matching the new upstream result. A deliberately changed tool result produced REPLAY_MISS before the next recorded model decision.

The first two native-playback attempts failed because matching included runtime timestamps/tool timings. Raw input snapshots demonstrated the difference. The corrected projection excludes only message timestamps and the framework's timing/usage audit channels. It preserves all text, tool calls, arguments, tool results, reasoning channels and control fields. Unit tests demonstrate that changed tool results and reasoning still change the semantic projection. Raw messages remain saved separately.

## Production constraints identified by this probe (historical)

The following list records the probe's original implementation gate. Production and its normal/feedback/failure playback are now implemented; see the dated NOTEBOOK.md entries, shared service, live MR01 pilot and current IMPLEMENTATION_PLAN.md. The probe's raw results and narrower claims remain unchanged. The full headline campaign is still executing.

- The Orchestrator must use typed planning/finalization actions; public results come from validated specialist receipts and grounded facts. Reject invalid model decisions instead of silently substituting a deterministic answer.
- Validate every requested child/tool action before execution. A parent can still request a forbidden or premature action; the pattern itself is not a policy engine.
- Enforce at most two semantic refinements and distinct plan hashes independently of the framework's tool-loop round limit.
- Bound one explicit schema repair separately from transport retries. Fast Agent defaults to two outer retries and the underlying OpenAI SDK also has retries; production must eliminate compounded retry budgets and verify one declared transport retry with a failure-injection check.
- Full six-role workflow capture and strict offline replay remain a production pilot gate. Successful one-role/native-tool playback does not establish a complete 900-comparison reproduction corpus.
- Apply before-call strict matching to all parent and detached-child model calls. Retain native tool-call IDs and upstream semantic receipts; reject missing, corrupt, changed or simulated cassettes.
- Freeze exact prompt/schema/tool/model/lock/cohort identities before the headline campaign. Probe fixtures, failures and injected controls stay outside its denominator.

See IMPLEMENTATION_PLAN.md for the next gates and NOTEBOOK.md for commands and evidence.

## Frozen current-source reference

`configs/probe_reference.json` binds the current environment proof to 125 source/configuration/capture integrity hashes:

- Seed capture: `20260930T202057Z-decision-fa9245` — three profiles, nine actual provider requests, strict validated intents and isolation checks; passed.
- Parent/child feedback control: `20260930T203129Z-agents-tools-e92e7b` — current-source repeat of the complete guarded live loop; passed, 24 provider requests, about 1320.57 seconds.
- Native tool-call capture/playback: `20260930T202936Z-tool-playback-827065` — native calls, real tool execution and changed-upstream-result rejection; passed.
- `make probe-replay` re-executes the frozen seed/native-tool references without model access. It checks 24 deliberately mismatched semantic/config/model/lock lookups, reruns the tools and rejects the native changed-result control. This is **environment proof replay**, not complete parent/child application replay or the assignment's `make reproduce` deliverable.

The earlier attempts remain preserved. Current references do not overwrite their raw responses, results or dispositions.
