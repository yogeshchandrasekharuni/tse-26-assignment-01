# Natural feedback example in the working report

Report page 4 now leads with the actual source of MR01-b010/seed104729, an original live headline execution. It records 35 visible observations across July 2025-June 2026 and 63 including available required lookbacks. Natural sparsity triggers a full CSV rescan and diagnostic Region; the unchanged counts and canonical hash confirm the sparse selection. Reviewer changes REFINE to ACCEPT_LIMITED, while the immutable query stays fixed. This is not an injected index fault or an additional campaign sample.

[The executed evidence check](check_evidence.py), [actual output](evidence-check.log) and [packet](evidence-check.json) independently filter the frozen CSV with integer predicates, check both recorded plans/selections/aggregates, the two real reviews, all six model roles, five tool receipts and grounded caveats. The packet hashes the original capture, raw CSV, case and freshly reproduced evidence. An initial ad hoc field inspection used guessed attribute names; strict model AttributeErrors exposed that inspection mistake before this checked script was authored from the actual models. No production contract was changed.

Actual command:

```sh
PYTHONHASHSEED=0 .venv/bin/python scripts/replay_case_leg.py --case MR01-b010-s104729 --leg source
```

[Playback output](replay.log) records a matched completed source with sixteen decisions and zero network attempts. All five freshly recomputed statistical result objects match the live capture. This is one-leg reproduction, not full900 clean-checkout reproduction.

`make report-draft` produced twelve visibly marked pages. [Render check](render-check.json) verifies all 23 current input hashes and compares every page raster to the prior committed draft: only page 4 changes. [Page 4](page-04.png) was opened and visually inspected for readable table/body text, complete trace references, spacing, footer separation and absence of clipping or overlap. The other eleven page rasters are unchanged; final twelve-page inspection will be performed on the final PDF bytes after the full campaign.

[Full check log](make-check.log) records exit0: 87 Python tests in62.49seconds, Python/delivery-script lint/format/types, generated contract freshness, three frontend parser tests and frontend TypeScript/Vite build/lint. The standalone evidence checker passes Ruff lint/format. Inference continues in the original process with frozen production, prompts, seeds, configuration, evaluation and data unchanged. Actual dashboard catch-up and final report/submission checks remain pending.
