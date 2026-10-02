# Preliminary source-leg diagnosis: MR01-b011-s130363

This eligible pair is an output-contract violation: the source fails and the shuffled follow-up completes. No final campaign ranking, rate or numerical metamorphic counterexample is claimed.

The source parent response001 delegates the Price role with purpose public_comparison. Price response002 contains valid JSON syntax but an invalid role-specific purpose: price_stats requires statistics. Trace event4 records the literal validation error; event5 records a pending repair. The already scheduled Supply response then reaches the controller while Price still owns the pending repair, producing AGENT_POLICY_ERROR at SCANNING. No final numeric comparison ran.

This agrees with the previously inspected purpose/repair-policy mechanism, now on an untransformed source leg and another query/seed. It does not show that row permutation caused a numeric fault or that there are two distinct underlying bugs. Data selection, invalid-relation and harness explanations remain separate from the observed raw validation/control error.

The actual command `PYTHONHASHSEED=0 .venv/bin/python scripts/replay_case_leg.py --case MR01-b011-s130363 --leg source` matched the four captured decisions and the same failure through the current production playback service. The preserved comparison under 20261002T194912Z records zero network attempts. This is reproduction of one captured failure, not a new live sample or another logical MR pair. The minimal invalid-intent diagnostic in the earlier MR01-b003-s155921 diagnosis illustrates the same schema boundary; it is not an independent live reproducer.

A prospective mitigation is repair-aware sequential delegation or explicit deferral of remaining batch children. It would require a separately versioned implementation/campaign; the running headline inputs are unchanged.
