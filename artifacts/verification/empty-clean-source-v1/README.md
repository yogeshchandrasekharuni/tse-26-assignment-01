# Clean-source check of the archived empty example

At2026-10-03T21:22:55 UTC, a fresh detached committed `42a1d6e` checkout passed `check.py` with exit0. Its initial git status was empty; original ignored web-runtime files and Langfuse credentials were absent. The command reused the existing locked Python interpreter and packages, with PYTHONPATH bound to the fresh source. This is a targeted clean-source proof, not fresh dependency setup or full900-comparison reproduction.

Actual in-process API requests read the empty analysis, all twelve monthly records, the unchanged raw trace, its one-refinement workflow and first/last captured model turns without network attempts. Current production `run_analysis` then executed strict Fast Agent playback with fresh tools:16 decisions, zero socket attempts and canonical SHA-256 `a420df83144fbabbce637488656c8d0a170c0bde097f84d561f59068eaccabd7`. All98 original archived files remained byte-identical.

`invocation.json` records the actual command/revision/times; `check.log` is its actual output and `result.json` its assertions. `playback/` preserves the recomputed run copied from the owned temporary checkout before removal. Raw metadata retains that run's historic relative output location. No model was called and no headline sample was added.
