"""Validate closed live projections locally, without ingestion or duplicated payloads."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json
from housing.observability.langfuse_plan import IMPLEMENTATION_FILES, PROJECTION_REVISION, project_capture


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, choices=("prefix.json", "complete.json"))
    args = parser.parse_args()
    packet = Path(__file__).resolve().parent
    destination = packet / args.output
    if destination.exists():
        raise ValueError("Preserve previous preflight proof; use a new version instead of overwriting")
    campaign = ROOT / "artifacts/campaigns/headline-live-v1"
    runs = sorted(run for run in campaign.glob("cases/*/attempt-*/*/runs/*") if run.is_dir())
    closed = [run for run in runs if (run / "terminal.json").is_file()]
    unfinished = [str(run.relative_to(ROOT)) for run in runs if run not in closed]
    complete = (campaign / "finished.json").is_file()
    if args.output == "complete.json" and not complete:
        raise ValueError("Complete preflight requires a closed campaign")
    rows = []
    for run in closed:
        projection = project_capture(run)
        keys = {span.key for span in projection.spans}
        assert len(keys) == len(projection.spans)
        assert sum(span.parent_key is None for span in projection.spans) == 1
        assert all(span.parent_key is None or span.parent_key in keys for span in projection.spans)
        assert all(all(link in keys for link in span.link_keys) for span in projection.spans)
        terminal = json.loads((run / "terminal.json").read_bytes())
        rows.append(
            {
                "run_path": projection.run_path,
                "trace_id": projection.trace_id,
                "projection_sha256": semantic_hash(projection),
                "observations": len(projection.spans),
                "model_decisions": terminal["model_decisions"],
                "execution_status": terminal["status"],
                "derived_repairs": sum(
                    span.attributes.get("langfuse.observation.metadata.iteration_label_basis")
                    == "plan_and_invalid_decision"
                    for span in projection.spans
                ),
            }
        )
    write_json(
        destination,
        {
            "status": "verified_offline_projections_only",
            "checked_at_utc": datetime.now(UTC).isoformat(),
            "projection_revision": PROJECTION_REVISION,
            "campaign_closed_at_inventory": complete,
            "closed_captures_verified": len(rows),
            "zero_decision_terminal_captures": sum(row["model_decisions"] == 0 for row in rows),
            "observations": sum(row["observations"] for row in rows),
            "unfinished_captures_at_inventory": unfinished,
            "rows": rows,
            "source_hashes": {
                name: sha256_bytes((ROOT / name).read_bytes())
                for name in (*IMPLEMENTATION_FILES, str(Path(__file__).relative_to(ROOT)))
            },
            "interpretation": "Local validation of raw-capture projection and span structure; no model calls, network, HTTP acceptance, dashboard readback or browser proof.",
        },
    )
    print(
        f"Validated {len(rows)} closed projections; {len(unfinished)} unfinished captures retained; no delivery."
    )


if __name__ == "__main__":
    main()
