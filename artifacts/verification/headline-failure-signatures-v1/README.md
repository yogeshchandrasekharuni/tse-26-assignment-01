# Exact failure-signature inventory

The executed checker reads all terminal failure records in the frozen live corpus and groups the exact code, stage and message. It verifies274 failed physical attempts:233 scanning pending-repair guards,37 Reviewer repair-budget exhaustions, two accepted-stage composition guards and two historical model-profile startup errors. The output is [the bound signature inventory](../../../reports/data/headline-failure-signatures.json).

Of those attempts,272 failed legs occur in the latest900 eligible comparisons and contribute to210 contract-violating pairs. Two historical startup failures remain retained outside the final eligible outcomes. Interrupted prefixes receive no invented terminal. A pair can contain two failed legs and can touch more than one signature; the listed logical case counts overlap and must not be added as independent bases.

These are exact emitted signatures, not an automatic unique-cause classifier. The [ranked raw/minimal diagnoses](../headline-rca-v1/README.md) provide the stronger mechanism evidence for the selected representatives. This inventory changes neither the headline, primary statistical unit nor recorded model behavior.
