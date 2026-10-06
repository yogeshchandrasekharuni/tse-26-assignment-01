"""Validate a terminal-capture snapshot offline; this does not deliver observations."""

import json
from datetime import UTC, datetime
from pathlib import Path

from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.observability.langfuse import project_capture as legacy_projection
from housing.observability.langfuse_plan import PROJECTION_REVISION, project_capture

proof = Path(__file__).resolve().parent
terminals = sorted((ROOT / "artifacts/campaigns/headline-live-v1/cases").glob("*/attempt-*/*/runs/*/terminal.json"))
terminals.extend(sorted((ROOT / "artifacts/runtime/web").glob("*/runs/*/terminal.json")))
runs = []
for terminal in terminals:
    directory = terminal.parent
    if json.loads((directory / "run-manifest.json").read_bytes())["mode"] != "live":
        continue
    trace_hash = sha256_bytes((directory / "trace.jsonl").read_bytes())
    legacy, projection = legacy_projection(directory), project_capture(directory)
    keys = {span.key for span in projection.spans}
    ids = {projection.span_id(span.key) for span in projection.spans}
    assert len(keys) == len(ids) == len(projection.spans)
    assert projection.trace_id != legacy.trace_id
    assert ids.isdisjoint(legacy.span_id(span.key) for span in legacy.spans)
    assert all(span.parent_key is None or span.parent_key in keys for span in projection.spans)
    assert all(set(span.link_keys) <= keys for span in projection.spans)
    assert sha256_bytes((directory / "trace.jsonl").read_bytes()) == trace_hash
    corrections = [span.key.rsplit("/", 1)[-1] for span in projection.spans
                   if span.attributes.get("langfuse.observation.metadata.iteration_label_basis")
                   == "plan_and_invalid_decision"]
    runs.append({"run_path": str(directory.relative_to(ROOT)), "trace_sha256": trace_hash,
                 "terminal_sha256": sha256_bytes(terminal.read_bytes()),
                 "legacy_trace_id": legacy.trace_id, "plan_trace_id": projection.trace_id,
                 "plan_projection_sha256": semantic_hash(projection),
                 "observations": len(projection.spans), "derived_repair_events": corrections})
packet = {"status": "verified_offline_projection_snapshot", "checked_at_utc": datetime.now(UTC).isoformat(),
          "scope": "Completed physical headline/API live captures at initial scan. No delivery, new model call, rate, combined logical count or full-campaign completion claim.",
          "projection_revision": PROJECTION_REVISION, "physical_captures": len(runs),
          "captures_with_derived_repair_labels": sum(bool(run["derived_repair_events"]) for run in runs),
          "raw_trace_bytes_preserved": True, "all_legacy_and_new_observation_ids_disjoint": True,
          "runs": runs}
(proof / "completed-projection-snapshot.json").write_text(json.dumps(packet, indent=2) + "\n")
print(json.dumps({key: value for key, value in packet.items() if key != "runs"}, indent=2))
