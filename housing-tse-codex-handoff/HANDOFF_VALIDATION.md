# Handoff validation record

Validated on 25 September 2026. This record concerns the specification bundle only. No Fast Agent application, live model, housing MR experiment or report was built or measured.

- Actual 4-page assignment PDF: extracted and visually inspected all 4 rendered pages. Both delivered Draw.io files: parsed all 3 pages each; copied originals preserved with SHA-256.
- Official Fast Agent, Ollama and NIST sources reviewed; API compatibility is a required future probe, not an execution claim. Suggested Qwen model tag verified in its official catalog.
- All JSON files parsed. All 12 Draft 2020-12 schemas checked with jsonschema 4.26.0. Supplied request/output examples, all 30 candidate requests,10 MR definitions,6 agent-decision examples and48 fixture rows validated. Strict unknown-field rejection checked.
- Three fixed paired seeds and all 3 MR families checked. Per-MR source-query overrides preserve 30 distinct candidates. These are candidate inputs, not completed eligible experimental runs.
- Hand-calculated median, median-of-ratios, half-even serialization, null/count-change and Wilson interval anchors passed. Multiplicative/replication/additive algebra sanity checks passed.
- Independent temporary arithmetic feasibility check of the generator recipe produced the specified 34,560 positive in-range scenario observations and confirmed a nonempty source plus strict count-superset witness for all 30 planned MR05 candidates. No output snapshot or MAS result was substituted for the implementation's required frozen data/preflight. This check used the QA host runtime; byte determinism under the final locked Python 3.12 runtime remains an implementation gate.
- Local Markdown links, original-source hashes, full package inventory, CSV template column counts and Python utility syntax checked. ZIP CRC and file-by-file payload identity checked during packaging.

The QA validator can be rerun with `python3 tools/validate_handoff.py`; install jsonschema into an isolated environment for full schema checks. `python3 tools/check_math_examples.py` uses the standard library. The implementation must still generate/freeze the substantial data, run the real agents and loop, capture actual decisions, execute all 900 comparisons, compute the actual headline table/RCA, reproduce offline and write/render the 10-12-page report.
