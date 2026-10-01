# Fast Agent integration: verified surface versus project policy

Reviewed official documentation and repository on 25 September 2026. Live docs/main can move; pin the version actually installed and record a passing probe. No application was executed for this handoff.

## Verified official surface

| Claim | Official evidence | Use here |
|---|---|---|
| Distribution is `fast-agent-mcp`; import package is `fast_agent`; current inspected main declares Python>=3.12,<3.15 and version0.10.42 | [repository pyproject](https://raw.githubusercontent.com/evalstate/fast-agent/main/pyproject.toml) | Start with Python 3.12; try exact0.10.42 only if published/resolvable, otherwise select an available version and record the difference |
| Agent decorators and async application lifecycle are documented; named agent `.send()` is supported | [Python API](https://fast-agent.ai/agents/defining/python_api/) | Six named role agents; fresh context per role invocation |
| Constructor supports `config_path`, `parse_cli_args=False`, `quiet=True` | [class reference](https://fast-agent.ai/ref/class_reference/) | Explicit config in API/CLI embedding; don't let Uvicorn flags enter the agent CLI |
| Built-in chain, parallel, router, orchestrator and evaluator-optimizer patterns are documented | [workflows](https://fast-agent.ai/agents/workflows/) | Background vocabulary; bounded feedback remains project-owned Python logic |
| Pydantic/JSON structured output exists; `.structured(prompt, Model)` is documented | [structured outputs](https://fast-agent.ai/guides/structured-outputs/) | Optional after probe; default uses `.send()` JSON + strict Pydantic validation to keep small-model/replay behavior simple |
| Generic provider supports an OpenAI-compatible local endpoint | [additional providers](https://fast-agent.ai/models/providers/additional/) and [configuration](https://fast-agent.ai/ref/config_file/) | Local Ollama, explicit model name; no cloud credentials required |
| Internal `playback` and `passthrough` models are documented | [internal models](https://fast-agent.ai/models/internal_models/) | Playback supplies captured decisions; passthrough is only a lifecycle smoke test |
| Ollama model files support a seed parameter; its compatible endpoint has a documented supported-field subset | [Modelfile](https://docs.ollama.com/modelfile) and [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility) | Derive seeded local model profiles; verify resolved model/default parameters rather than assume a framework seed field |

Observed version is a **repository-main value**, not a claim that PyPI/latest release was installed here. Do not build against a guessed version from this handoff. Preserve dependency resolution/probe evidence in `artifacts/framework_probe/`. Do not transplant imports or classes from LangGraph, Pydantic AI or another framework and call them Fast Agent APIs.

## Minimal shape to verify

Illustrative adapter skeleton, intentionally without a fake seed argument or unverified decorator options:

```python
from fast_agent import FastAgent

fast = FastAgent("housing", parse_cli_args=False, quiet=True)

@fast.agent(name="reviewer", instruction="Return only the allowed review JSON.")
async def register():
    pass

async def invoke(prompt: str) -> str:
    async with fast.run() as agents:
        return await agents.reviewer.send(prompt)
```

Use explicit config path and the installed version's supported model/history configuration. Define one fresh isolated role context per invocation initially; avoid hidden conversation state. Validate the returned text with the project schema. `.structured()` may be adopted after a real provider+schema test, but do not depend on a model supporting native tools and structured responses simultaneously without checking. The official guide describes different structured-tool policies; they are optional here because the project's default JSON-intent dispatcher keeps those concerns separate.

## Mandatory probe gate before application implementation

Build a small `scripts/probe_fast_agent.py` and commit its test (not cached success text):
1. Resolve/import the exact distribution in the lock; save Python/package versions and signatures used.
2. Register two distinct role agents, start/close lifecycle, call each by name and validate a tiny project JSON schema. Confirm model picked from explicit profile, no interactive picker in automation.
3. Call a real local model with one sample planner/reviewer prompt. Parse JSON; verify an invalid/forbidden action is rejected by the controller rather than applied.
4. Demonstrate isolated history: source/follow-up and concurrent roles do not share messages.
5. Capture one real decision; replay it through the installed Fast Agent `playback` model in a fresh context. Assert exact matched decision, then execute a real project tool and validate its receipt.
6. Reject replay when prompt/tool-result/schema/seed hash changes; block external model calls during replay.
7. Verify three seeded model profiles exist and their immutable source/model digests and Modelfile seed defaults match manifest. Save requested/effective seed and whether reproducibility is only best effort on the machine.
8. Run a sparse/omitted-index fixture live and assert Reviewer REFINE leads to planner strategy and specialist-set changes. Store actual trace; never use the illustrative fixture trace as proof.

If any API differs, fix the adapter to the pinned official version and update this mapping. If no local model can run, complete unaffected coding/tests but mark live evaluation/report evidence as incomplete; never label a script-only system a finished Fast Agent MAS.

## Model seed strategy

The generated RequestParams field list inspected in the Python API does not document a universal seed field. Do not assume `RequestParams(seed=...)`, `.send(seed=...)` or a model query-string seed works. Default approach: create three local derived Ollama model names, one per seed, from the same frozen base model. Example **Ollama Modelfile**, not Fast Agent YAML:

```
FROM qwen2.5:7b-instruct
PARAMETER seed 104729
PARAMETER temperature 0.2
```

Create corresponding profiles for 130363 and155921 and select e.g. `generic.housing-qwen-s104729` in Fast Agent. Save the actual Modelfiles and resolved base/derived model digests. No changing seeds on repair calls; record each call's profile. Default seeds are per fresh role call; do not assume a single advancing RNG sequence across the entire workflow. Some providers ignore seed or provide best-effort reproducibility; a cloud fallback must declare `seed_supported=false` when appropriate and cannot claim full fixed effective seeds. Prefer the verified local profile for the reference campaign. A successful repeated text response alone does not prove seed propagation; inspect resolved model configuration and provider request/profile logs.

## Project JSON-intent tools

`PlanDecision`, `SpecialistDecision`, `ReviewDecision`, `ReportDecision`, `WorkflowState`, `ToolReceipt`, `run_analysis` and `DecisionCassette` are names defined by this application. They are **not** Fast Agent imports. Model agents do not receive shell, files, arbitrary SQL or network tools. Instead a project dispatcher takes their validated allowed intent, binds trusted dataset/query/selection arguments from state, and calls typed deterministic Python functions. Log both model decision and execution receipt. The model never supplies trusted input hashes or numeric results.

This design uses real model decisions and tool execution with role-specific capability boundaries. Describe it as intent dispatch, not as native framework function calling. If you later add a true MCP server, use exact documented server configuration/tool filtering for the pinned version, retain equivalent type/policy checks and establish live/replay parity before changing the experiment.

## Strict offline replay design

Use a `DecisionProvider` **project interface** with live and replay adapters, both returning the same parsed role decision. Live adapter calls Fast Agent and saves raw response text plus semantic prompt/action-schema/seed/version hashes. Replay adapter:

1. Build exactly the same semantic prompt from current upstream tool receipts and canonical request; find an exact cassette key. No timestamps, random run IDs or local paths enter prompt bytes.
2. Verify source live-campaign ID, response hash, role/schema/profile and seed. A captured invalid response can be replayed as invalid; never replace it with a corrected response.
3. Load that single captured conversation into a fresh Fast Agent role with `model="playback"` using the documented `load_prompt` + generation pattern. Then `.send()` the matched original prompt, parse the result and validate.
4. Run the current Python dispatcher/tools, controller, aggregator and comparators; record **new** receipts/traces. Source/follow-up results are recalculated, not loaded from the corpus.
5. A future upstream tool-result change changes the next prompt hash and must fail replay unless that exact live observation was captured. Reject nearest-match or stale cassettes.

The internal-model docs show loading a conversation then replaying responses. They do not establish exact semantic lookup, content-addressed storage, statistical independence or tool execution; those are mandatory project additions. Do not rely on undocumented replay matching guarantees. The project has no framework-native tool call transcripts in its default decision protocol, so it need not emulate MCP playback. A missing corpus is a real incomplete deliverable. Tiny authored fixture responses may be used for unit tests under `POLICY_SIMULATION` only.

## Adapter acceptance and configuration

`templates/fast-agent.example.yaml` is a minimal documented-shape starting config, not an all-version universal schema. Implementation must validate it in the probe and generate an explicit config per seed/mode. Native model history must be off or reset via fresh contexts. Model/dependency selection cannot change between source and follow-up. Commit `uv.lock`/frontend lockfile, config hashes and prompt bundle hashes. Local provider may need dummy key `ollama`; it is not a paid credential. Disable telemetry/exporters and external fetching for offline reproduction. Never hardcode private API keys.


See [REPRODUCIBILITY_CONTRACT.md](REPRODUCIBILITY_CONTRACT.md) for exact hash projections, volatile-field exclusions and the offline command acceptance protocol. Upstream **semantic** tool-receipt hashes exclude run IDs, durations, paths and trace sequence references; full byte hashes remain separate integrity evidence.
