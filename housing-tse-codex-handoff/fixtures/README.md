# Fixture provenance

Everything here is a small authored/generated test fixture, a planned control, or a hand-calculated output example. **No live MAS ran to produce these files.** The48-row low_support.csv is deliberately small to test feedback and exact arithmetic; it must never replace the 34,560-row headline snapshot. Its example output is calculated from its fixed rows and uses policy_simulation metadata plus zero placeholder lineage hashes. It is not a valid live-capture corpus.

Use metric_cases.json for arithmetic anchors, edge_case_matrix.json for implementation test recipes, feedback_scenario.json for an intentionally omitted index partition, and agent_decisions.json for schema/unit tests only. The implementation must record a genuine live feedback trace and a genuine model decision corpus separately. Invalid/null cases stay visible in harness output. No fixture failure counts enter measured headline rates.
