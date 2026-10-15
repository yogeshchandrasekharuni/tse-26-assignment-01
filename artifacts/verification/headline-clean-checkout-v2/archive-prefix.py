"""Preserve the operator-stopped per-leg-GC replay without relabeling it complete."""

import gzip
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from housing.evaluation.aggregate import case_semantics
from housing.evaluation.models import CaseResult
from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json

packet = Path(__file__).resolve().parent
checkout = Path(
    "/private/var/folders/w0/q9j5b5yn2p3_16nhb0s4gdd40000gp/T/housing-clean-_tyylz7m/repository"
)
relative = Path("artifacts/reproductions/20261015T091331Z")
source = checkout / relative
cases = list((source / "cases").glob("*/result.json"))
assert 0 < len(cases) < 900
assert not (source / "reproduction-comparison.json").exists()
for path in cases:
    case = CaseResult.model_validate_json(path.read_bytes())
    original = CaseResult.model_validate_json(
        (ROOT / "artifacts/campaigns/headline-live-v1/cases" / path.parent.name / "result.json").read_bytes()
    )
    assert semantic_hash(case_semantics(case)) == semantic_hash(case_semantics(original))
files = sorted(path for path in source.rglob("*") if path.is_file())
hashes = {str(path.relative_to(checkout)): sha256_bytes(path.read_bytes()) for path in files}
archive = packet / "operator-stopped-replay-20261015T091331Z.tar.gz"
with archive.open("xb") as output:
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as bundle:
            for path in files:
                assert not path.is_symlink()
                bundle.add(path, arcname=str(path.relative_to(checkout)), recursive=False)
observed = {}
with tarfile.open(archive, "r:gz") as bundle:
    for entry in bundle:
        assert entry.isfile() and entry.name.startswith(str(relative) + "/")
        stream = bundle.extractfile(entry)
        assert stream is not None
        observed[entry.name] = sha256_bytes(stream.read())
assert observed == hashes
write_json(
    packet / "archive.json",
    {
        "status": "verified_preserved_operator_stopped_replay",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "completed_cases": len(cases),
        "completed_case_semantics": "Every completed case matches its live reference, including historical seed attribution; this prefix is not full900 proof",
        "partial_run_directories": [
            str(path.relative_to(checkout))
            for path in source.glob("cases/*/attempt-*/*/runs/*")
            if path.is_dir() and not (path / "terminal.json").is_file()
        ],
        "archive": str(archive.relative_to(ROOT)),
        "archive_sha256": sha256_bytes(archive.read_bytes()),
        "archive_bytes": archive.stat().st_size,
        "files": len(files),
        "file_hashes": hashes,
        "source_progress": json.loads((source / "progress.json").read_bytes()),
        "interpretation": "Auxiliary replay deliberately stopped for resource-policy replacement. No fresh model sample, natural violation or completed full reproduction is claimed.",
    },
)
print(f"Preserved {len(files)} files; all {len(cases)} completed prefix cases match; full900 remains pending.")
