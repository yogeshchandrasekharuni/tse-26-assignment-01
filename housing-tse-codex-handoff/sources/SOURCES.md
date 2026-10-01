# Sources and provenance

The actual4-page assignment PDF was extracted and visually inspected page by page. Both delivered Draw.io XML files were read, including all 3 pages each. Historical `/mnt/data` paths were unavailable on this machine; the exact-named files were located in the user's Downloads folder and copied unmodified under originals/. Source checksums are in originals_sha256.json. An additional later workspace diagram was inspected during discovery but is not substituted for either delivered file.

The ChatGPT reference conversation was read as background data. Claims in its assistant summary were verified against the actual PDF/drawings where possible; the original assignment governs. The no-fills diagram differs structurally from the earlier original by merging Criteria Interpreter into Orchestrator. Latest user preference is white page/subtle box fills, irrespective of the filename.

Official framework/provider/statistics sources reviewed16 October 2026 follow. These establish documented API surface only; no Fast Agent package, local model or application was run for this package. Live documentation can move. The implementation must pin and probe actual installed APIs and model configuration.

- **F01** [Fast Agent Python API](https://fast-agent.ai/agents/defining/python_api/): Agent definition, lifecycle and named calls; no universal seed in generated RequestParams list.

- **F02** [Fast Agent class reference](https://fast-agent.ai/ref/class_reference/): Embedding constructor parameters and documented workflow methods.

- **F03** [Fast Agent workflows](https://fast-agent.ai/agents/workflows/): Conceptual workflow vocabulary; application loop remains project-owned.

- **F04** [Fast Agent structured outputs](https://fast-agent.ai/guides/structured-outputs/): Pydantic/JSON support; model/provider capability caveats.

- **F05** [Fast Agent internal models](https://fast-agent.ai/models/internal_models/): Playback and passthrough exist; exact cassette matching is project responsibility.

- **F06** [Fast Agent additional providers](https://fast-agent.ai/models/providers/additional/): Generic OpenAI-compatible endpoint configuration.

- **F07** [Fast Agent configuration](https://fast-agent.ai/ref/config_file/): Generic local base_url/api_key configuration shape.

- **F08** [Fast Agent repository pyproject](https://raw.githubusercontent.com/evalstate/fast-agent/main/pyproject.toml): Observed main0.10.42, Python>=3.12,<3.15; not an installation/publication claim.

- **F09** [Fast Agent repository](https://github.com/evalstate/fast-agent): Official project/distribution and top-level examples.

- **O01** [Ollama Modelfile reference](https://docs.ollama.com/modelfile): Seed/temperature model parameters; effective profile must be verified.

- **O02** [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility): Local compatible endpoint and provider field subset.

- **S01** [NIST confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm): Wilson score interval discussion; unit/estimand remain project design.


- **O03** [Ollama qwen2.5:7b-instruct model tag](https://ollama.com/library/qwen2.5:7b-instruct): suggested model tag verified; model not downloaded or run here.
