"""Check deliverable paths and actual local credential values without printing secrets."""

import re
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote

from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json

packet = Path(__file__).resolve().parent
names = {
    name.decode()
    for name in subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).split(b"\0")
    if name
}
assert "observability/langfuse/.env" not in names
assert not any(
    name.startswith((".venv/", ".cache/", ".python/", "frontend/node_modules/", "tmp/", "artifacts/runtime/"))
    for name in names
)
credentials: list[bytes] = []
for line in (ROOT / "observability/langfuse/.env").read_text().splitlines():
    if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    value = value.strip().strip("\"'")
    if re.search(r"SECRET|PASSWORD|KEY|TOKEN", key.upper()) and len(value) >= 8:
        credentials.append(value.encode())
assert len(credentials) >= 5
archive_members = 0
byte_count = 0
for name in sorted(names):
    path = ROOT / name
    assert path.is_file(), name
    content = path.read_bytes()
    byte_count += len(content)
    assert not any(secret in content for secret in credentials), f"Credential value detected in {name}"
    if name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(path, "r:gz") as archive:
            for member in archive:
                if member.isfile():
                    stream = archive.extractfile(member)
                    assert stream is not None
                    body = stream.read()
                    assert not any(secret in body for secret in credentials), f"Credential in archive {name}"
                    archive_members += 1
documents = (
    "README.md",
    "SUBMISSION.md",
    "DEMONSTRATION.md",
    "EVIDENCE_INDEX.md",
    "IMPLEMENTATION_PLAN.md",
    "reports/README.md",
    "observability/langfuse/README.md",
    "REPLAY_METADATA.md",
)
local_links = 0
for name in documents:
    path = ROOT / name
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
        target = target.strip("<>").split("#", 1)[0]
        if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue
        destination = (path.parent / unquote(target)).resolve()
        assert destination.is_relative_to(ROOT) and destination.exists(), (name, target)
        local_links += 1
write_json(
    packet / "inventory.json",
    {
        "status": "verified_precommit_candidate_inventory",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "candidate_files_scanned": len(names),
        "candidate_bytes_scanned": byte_count,
        "candidate_path_inventory_sha256": semantic_hash(sorted(names)),
        "historical_archive_members_scanned": archive_members,
        "local_credential_values_checked": len(credentials),
        "credential_matches": 0,
        "current_document_local_links_checked": local_links,
        "source_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "interpretation": "All tracked and nonignored candidate files before commit, plus decompressed historical tar members, checked against actual ignored local secret/key/password values. No values emitted. Generated receipt/log completion bytes and later committed-tree ZIP inventory are verified separately.",
    },
)
print(
    f"Verified {len(names):,} candidate files, {archive_members:,} archive members and {local_links} local links; zero credential matches."
)
