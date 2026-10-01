# Housing Trends MAS: Codex implementation handoff

Prepared 16 October 2026 for the IIIT Hyderabad TSE assignment, team of two. The assignment lists this same date as the deadline; no submission hour or extension is inferred. This bundle specifies the implementation. **It contains no built application, completed experiment, measured violation rates, recorded model corpus, or finished report.**

## Start here

1. Extract this folder into the intended repository (or copy its contents to `handoff/`). Preserve the originals in `sources/originals/`.
2. Give Codex `CODEX_PROMPT.md` as the opening message and point it to this folder. If these documents are under `handoff/`, copy `AGENTS.md` to the repository root after reconciling existing repository instructions.
3. Read `SPEC.md`, then `DATA_CONTRACT.md`, `MR_CATALOG.md`, `ARCHITECTURE.md`, and `FAST_AGENT_INTEGRATION.md`. Work through `IMPLEMENTATION_PLAN.md` in order.
4. Start the API compatibility probe before building UI polish. Freeze the snapshot before collecting results. Run one end-to-end reorder MR before scaling the harness.
5. Use the supplied templates as inputs to implementation, not as measured evidence. `templates/base_candidates.json` contains 30 distinct *candidate* requests; each MR still needs its own recorded eligibility/effect checks and 30 valid bases.

## Package contents

| File/folder | Purpose |
|---|---|
| [SPEC.md](SPEC.md) | Normative scope, output contract, workflow, endpoints, UI and acceptance |
| [CODEX_PROMPT.md](CODEX_PROMPT.md) | Complete directive to paste into Codex |
| [AGENTS.md](AGENTS.md) | Repository coding and evidence rules |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Phased work, gates, team split, completion checks |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Six model agents, deterministic tools, graph and state transitions |
| [FAST_AGENT_INTEGRATION.md](FAST_AGENT_INTEGRATION.md) | Verified framework surface, project abstractions, live/replay and seed probes |
| [DATA_CONTRACT.md](DATA_CONTRACT.md) | Row grain, validation, 24-month generator recipe and provenance |
| [MR_CATALOG.md](MR_CATALOG.md) | Ten exact relations with subdomains, witnesses, tolerances and faults |
| [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md) | Sampling, statuses, seed pairs, denominators, Wilson intervals and RCA |
| [TEST_ACCEPTANCE.md](TEST_ACCEPTANCE.md) | Concrete tests, mutation controls and evidence gates |
| [REPORT_OUTLINE.md](REPORT_OUTLINE.md) | Twelve-page report allocation and requirement-to-evidence mapping |
| [DECISIONS.md](DECISIONS.md) | Resolved ambiguities, implementation choices and change procedure |
| [REPRODUCIBILITY_CONTRACT.md](REPRODUCIBILITY_CONTRACT.md) | Stable hashes, strict replay boundary and exact offline acceptance |
| `schemas/` | Draft 2020-12 schemas for requests, results, decisions, traces, MR definitions/results |
| `templates/` | Seeds, generator, experiment, candidates, report table, provenance and notebook/AI-use templates |
| `fixtures/` | Small illustrative inputs and exact arithmetic checks; never headline data |
| `prompts/` | Role-specific model instructions to adapt and freeze |
| `sources/` | Source register, page-level assignment mapping, original PDF and both delivered diagrams |
| `tools/` | Handoff-only validation and arithmetic sanity checks |

## What can run in this bundle

`python3 tools/validate_handoff.py` checks package structure, hashes, JSON, local links and distinct candidate requests. It uses the standard library. If `jsonschema` is installed it additionally validates schemas and examples. `python3 tools/check_math_examples.py` checks the small hand-calculated fixtures and confidence-interval anchors. These commands validate this handoff; they do not evaluate a housing MAS.

## Required commands in the future application

The implementation must create these targets; they are **not present as working application commands in this handoff**:

```sh
make setup                 # install exactly locked dependencies; network allowed here
make data                  # regenerate frozen bytes and compare their SHA-256
make check                 # lint, types, meaningful unit/integration tests, frontend build
make dev                   # backend + frontend, local model if configured
make evaluate-live         # seeded local Fast Agent execution; capture decision corpus
make reproduce             # OFFLINE: execute Fast Agent playback + tools + MRs; recompute table
make report                # render final 10-12-page PDF from actual evidence
make submission-check      # verify all assignment requirements, artifacts, hashes, page count
```

Offline reproduction assumes `make setup` has completed and the submitted snapshot plus **live-captured** cassette corpus is present. If zero-network installation on a fresh machine is needed, also ship a platform-specific wheelhouse or exported container image; do not describe first-time package downloads as offline. The reference headline run must include at least 30 eligible distinct bases per MR and all three seed pairs. Missing cassettes or missing runs must fail visibly.

## Authority and changes

The assignment PDF is the source for coursework requirements. This bundle's explicit defaults resolve ambiguities permitted by p.4. `SPEC.md` governs semantics; schemas govern syntax; `MR_CATALOG.md` governs comparisons; `EVALUATION_PROTOCOL.md` governs statistics. A conflict is a defect to repair before measurement, not permission to choose a convenient interpretation. Version and re-freeze all affected artifacts when changing a contract. Source copies were found in the user's Downloads folder because the referenced historical `/mnt/data` paths do not exist on this host.


See [FILE_INDEX.md](FILE_INDEX.md) for individual files and [HANDOFF_VALIDATION.md](HANDOFF_VALIDATION.md) for checks performed on this package. These checks are distinct from the future application evaluation.
