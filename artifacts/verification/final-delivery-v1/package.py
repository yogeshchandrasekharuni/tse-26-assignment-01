"""Create and verify a committed-tree source archive after final evidence is committed."""

import json
import subprocess
import zipfile
from datetime import UTC, datetime

from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json

assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip()
audit = json.loads((ROOT / "artifacts/verification/final-delivery-v1/audit.json").read_bytes())
assert audit["status"] == "verified_current_deliverable_files"
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
tracked = {
    name.decode()
    for name in subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "-z", revision], cwd=ROOT
    ).split(b"\0")
    if name
}
required = {
    "output/pdf/housing-report.pdf",
    "reports/data/pdf-qa.json",
    "reports/data/clean-checkout.json",
    "reports/data/diagnosis.json",
    "data/frozen/dallas-synth-v1.csv",
    "uv.lock",
    "frontend/package-lock.json",
    "NOTEBOOK.md",
    "AI_USE.md",
    "SUBMISSION.md",
    "DEMONSTRATION.md",
    "artifacts/observability/headline-delivery-v1/verification.json",
}
assert required <= tracked
assert "observability/langfuse/.env" not in tracked
assert not any(
    name.startswith((".venv/", ".cache/", ".python/", "frontend/node_modules/", "tmp/", "artifacts/runtime/"))
    for name in tracked
)
destination = ROOT / "output/submission"
destination.mkdir(parents=True, exist_ok=True)
archive = destination / "housing-tse-submission.zip"
assert not archive.exists()
subprocess.run(
    ["git", "archive", "--format=zip", "--prefix=housing-evidence/", "--output", str(archive), revision],
    cwd=ROOT,
    check=True,
)
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    paths = {name.removeprefix("housing-evidence/") for name in bundle.namelist() if not name.endswith("/")}
    assert paths == tracked
    assert sha256_bytes(bundle.read("housing-evidence/output/pdf/housing-report.pdf")) == audit["pdf_sha256"]
    canonical = ROOT / "artifacts/campaigns/headline-live-v1"
    for relative, expected in json.loads((canonical / "artifact_hashes.json").read_bytes()).items():
        assert (
            sha256_bytes(bundle.read("housing-evidence/artifacts/campaigns/headline-live-v1/" + relative))
            == expected
        )
write_json(
    destination / "manifest.json",
    {
        "status": "verified_committed_source_archive",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git_revision": revision,
        "tested_code_revision": audit["tested_revision"],
        "archive_sha256": sha256_bytes(archive.read_bytes()),
        "archive_bytes": archive.stat().st_size,
        "tracked_files": len(tracked),
        "file_inventory_sha256": semantic_hash(sorted(tracked)),
        "pdf_sha256": audit["pdf_sha256"],
        "canonical_live_files_rechecked_inside_zip": len(
            json.loads((canonical / "artifact_hashes.json").read_bytes())
        ),
        "interpretation": "Exact committed tree, not Git history or installed dependencies. Locked setup precedes offline reproduction; local credentials, caches, model weights and runtime jobs are excluded.",
    },
)
print(
    f"Verified source ZIP: {len(tracked):,} committed files, {archive.stat().st_size:,} bytes, complete canonical live inventory rechecked."
)
