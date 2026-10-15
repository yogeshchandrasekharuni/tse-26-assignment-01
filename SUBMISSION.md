# Submission inventory

Verified delivery: all 900 live comparisons, reviewed diagnosis, desktop/mobile UI and local dashboard proof are complete. Initially clean revision 8eb6727d passed offline setup/data/check/framework playback and all 900 comparisons. The twelve-page final PDF has been visually inspected on every page. Actual `make submission-check` exited0, including 106 Python tests and frontend/schema checks. Historical failed and interrupted attempts remain preserved.

| Deliverable | Location | Contents |
| --- | --- | --- |
| Git repository | This repository | Application, exact contracts/tools, Fast Agent adapter, tests, locked environment and editable sources |
| Final report | [PDF](output/pdf/housing-report.pdf), [exact all-page QA](reports/data/pdf-qa.json) | Twelve visually inspected pages: system/data, all ten justified MRs, base-level rates/nominal Wilson intervals, actual loop, ranked diagnosis, limitations and substantive AI reflection |
| Architecture note | [DESIGN_NOTE.md](DESIGN_NOTE.md) | Sole public Orchestrator, internal roles, marked feedback cycle, frozen source and ten MR sketches; no earlier hand-in is claimed |
| Frozen data | [CSV](data/frozen/dallas-synth-v1.csv), [manifest](data/manifests/dallas-synth-v1.json) | 34,560 generated observations over 24 months; explicitly synthetic |
| Experiment corpus | [Headline](artifacts/campaigns/headline-live-v1/headline.json), [complete integrity audit](artifacts/verification/headline-final-v1/audit.json) | Ten MRs × 30 distinct bases × 3 paired seeds = 900 comparisons; all attempts and source lineage retained |
| Reviewed diagnosis | [Diagnosis](reports/data/diagnosis.json), [raw/minimal replay packet](artifacts/verification/headline-rca-v1/README.md) | MR03/MR05/MR07 share one demonstrated representative mechanism; three actual four-decision reductions, with alternatives and limits |
| Full offline verification | [Clean-checkout result](reports/data/clean-checkout.json), [matched900 comparison](artifacts/reproductions/20261015T135745Z/reproduction-comparison.json), [final audit](artifacts/verification/final-delivery-v1/audit.json) | Initially clean committed code; current tools/control/relations re-executed, exact semantics matched, zero network/new inference; prior unsuccessful runs kept separately |
| Final checks | [Command receipt](artifacts/verification/final-delivery-v1/submission-command.json), [closed log](artifacts/verification/final-delivery-v1/submission-check.log) | Actual exit0;106 Python tests, generated contracts, frontend checks and evidence/PDF consistency |
| Local trajectory dashboard | [Dashboard guide](observability/langfuse/README.md), [current deep links](artifacts/observability/current-demo-index.json) | Actual readback for 1,196 terminal trajectories/35,356 observations; separate interrupted prefixes; natural feedback, repair/failure, ordinary flow and labeled injected control |
| Execution and AI record | [NOTEBOOK.md](NOTEBOOK.md), [AI_USE.md](AI_USE.md), [recovery](RUNTIME_RECOVERY.md), [replay correction](REPLAY_METADATA.md) | Commands, versions, actual results, mistakes, retained failures, lost temporary console and correction scope |
| Requirement evidence | [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md) | Links to actual proof with statistical and historical scopes kept explicit |
| Professor walkthrough | [DEMONSTRATION.md](DEMONSTRATION.md) | Practical browser routes and replay demonstration; no fresh inference needed |

All 690 numerically comparable pairs satisfy their declared projections. The other 210 pairs have eligible output-contract violations. Those failures remain findings; successful reproduction must preserve them. The primary rate uses a base with any violation across seeds 104729/130363/155921, with 30 completed bases per MR. Overlapping designed slices and successful-source reuse limit generalization.

## Run and reproduce

```sh
make setup             # locked Python/frontend dependencies; initial downloads allowed
make data              # independently regenerate and verify frozen bytes
make check             # Python, generated contracts and frontend checks
make dev               # application at 127.0.0.1:5173, API at 127.0.0.1:8000
make reproduce         # all 900 comparisons, current tools/control, network denied
make report            # final evidence-bound PDF
make submission-check  # checks and strict deliverable consistency
```

Offline reproduction requires completed setup and the captured evidence. It needs neither a model server nor paid credentials and never downloads a model. `make evaluate-live` verifies a completed corpus without changing its bytes or resampling; fresh live analysis additionally requires the documented pinned local model profiles. `make clean-checkout` requires a Git checkout and exercises offline setup/data/check/framework playback/full reproduction from a committed revision.

`make langfuse-up` starts the isolated local Docker project at localhost19300. Existing local data/credentials survive ordinary down/up. On a fresh machine initialize it as documented, then import the recorded examples or full corpus; imports make no model calls. Keep the ignored local environment file out of submissions. The dashboard is a readable projection; raw captures are canonical.

The specified coursework deadline is 16 October 2026 and team size is two. Author names and an earlier design-note submission have not been invented. The repository is the authoritative Git deliverable. The local packaging helper `artifacts/verification/final-delivery-v1/package.py` creates `output/submission/housing-tse-submission.zip` only from a clean committed tree, with a separately verified manifest. That convenient snapshot excludes Git history, caches, model weights and local credentials. Its manifest records the exact packaged commit, tested code revision, ZIP hash, PDF hash and full canonical-live inventory readback.
