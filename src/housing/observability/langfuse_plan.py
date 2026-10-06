"""Plan-aware derivation; the exercised legacy exporter and raw captures stay intact."""

import json
from pathlib import Path

from pydantic import JsonValue

from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.observability.iterations import iteration_labels, natural
from housing.observability.langfuse import CaptureProjection
from housing.observability.langfuse import project_capture as legacy_projection

PROJECTION_REVISION = "housing-langfuse-plan-2"
IMPLEMENTATION_FILES = (
    "src/housing/observability/iterations.py",
    "src/housing/observability/langfuse.py",
    "src/housing/observability/langfuse_plan.py",
    "src/housing/reporting/usage.py",
)


def project_capture(directory: Path) -> CaptureProjection:
    """Preserve the wire schema, version all derived IDs and annotate proven repairs."""
    legacy = legacy_projection(directory)
    projection = legacy.model_copy(deep=True)
    events: list[dict[str, JsonValue]] = [
        json.loads(line) for line in (directory / "trace.jsonl").read_bytes().splitlines()
    ]
    labels = iteration_labels(events)
    source_hashes = {name: sha256_bytes((ROOT / name).read_bytes()) for name in IMPLEMENTATION_FILES}
    implementation = semantic_hash({"revision": PROJECTION_REVISION, "sources": source_hashes})
    by_key = {span.key: span for span in projection.spans}
    for span in projection.spans:
        span.attributes["langfuse.observation.metadata.export_version"] = PROJECTION_REVISION
        span.attributes["langfuse.observation.metadata.exporter_sha256"] = implementation
        span.attributes["langfuse.observation.metadata.legacy_trace_id"] = legacy.trace_id
        tags = span.attributes.get("langfuse.trace.tags")
        if isinstance(tags, list):
            span.attributes["langfuse.trace.tags"] = [*tags, "plan-aware-v2"]
    for index, (event, label) in enumerate(zip(events, labels, strict=True)):
        span = by_key[f"event-{index:03d}"]
        span.attributes["langfuse.observation.metadata.recorded_iteration"] = natural(event["iteration"])
        span.attributes["langfuse.observation.metadata.iteration"] = label.display_iteration
        span.attributes["langfuse.observation.metadata.iteration_label_basis"] = label.basis
        if label.basis == "recorded":
            continue
        # The annotator proved that this immediately follows an invalid role decision.
        preceding = by_key[f"event-{index - 1:03d}"]
        owner = by_key.get(preceding.parent_key or "")
        generation = by_key.get(owner.key.replace("agent-", "generation-")) if owner else None
        if (
            owner is None
            or owner.kind != "agent"
            or generation is None
            or generation.attributes.get("langfuse.observation.metadata.role") != event["actor"]
            or generation.attributes.get("langfuse.observation.metadata.iteration") != label.display_iteration
        ):
            raise ValueError("The corrected repair has no proven role/pass owner")
        span.parent_key = owner.key
        span.link_keys = tuple(dict.fromkeys((*span.link_keys, preceding.key)))
        span.attributes["langfuse.observation.metadata.iteration_annotation"] = (
            "Raw tag retained in input; displayed pass follows active plan and preceding invalid decision"
        )
    # A legacy default-zero repair could extend the initial role's duration. Rebuild
    # role envelopes from their generation and the now correctly attached events.
    for span in projection.spans:
        if span.kind == "generation" and span.parent_key is not None and span.parent_key != "orchestrator":
            parent = by_key[span.parent_key]
            parent.start_ns, parent.end_ns = span.start_ns, span.end_ns
    for span in projection.spans:
        if (
            span.key.startswith("event-")
            and span.parent_key is not None
            and span.parent_key != "orchestrator"
        ):
            parent = by_key[span.parent_key]
            parent.end_ns = max(parent.end_ns, span.end_ns)
    projection.trace_id = semantic_hash(
        [PROJECTION_REVISION, implementation, legacy.run_path, legacy.trace_id]
    )[:32]
    projection.exporter_sha256 = implementation
    projection.artifact_hashes.update(source_hashes)
    # Langfuse observation IDs must remain distinct across derivations as well as
    # traces, so a new trace cannot overwrite observations from legacy readback.
    namespace = f"{PROJECTION_REVISION}/{implementation}/"
    for span in projection.spans:
        span.key = namespace + span.key
        span.parent_key = namespace + span.parent_key if span.parent_key else None
        span.link_keys = tuple(namespace + key for key in span.link_keys)
    return projection
