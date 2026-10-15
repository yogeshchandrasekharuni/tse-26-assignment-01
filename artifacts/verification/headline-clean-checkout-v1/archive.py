"""Preserve every generated file from the failed full900 playback in a compact archive."""

import gzip
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from housing.identity import ROOT, sha256_bytes, write_json

PACKET = Path(__file__).resolve().parent
SOURCE_ROOT = Path(
    "/private/var/folders/w0/q9j5b5yn2p3_16nhb0s4gdd40000gp/T/housing-clean-0s3tn2z5/repository"
)
RELATIVE = Path("artifacts/reproductions/20261015T051521Z")
source = SOURCE_ROOT / RELATIVE
files = sorted(path for path in source.rglob("*") if path.is_file())
assert len(list((source / "cases").glob("*/result.json"))) == 900
assert not (source / "reproduction-comparison.json").exists()
hashes = {str(path.relative_to(SOURCE_ROOT)): sha256_bytes(path.read_bytes()) for path in files}
archive = PACKET / "failed-reproduction-20261015T051521Z.tar.gz"
with archive.open("xb") as output:
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as bundle:
            for path in files:
                assert not path.is_symlink()
                bundle.add(path, arcname=str(path.relative_to(SOURCE_ROOT)), recursive=False)
observed = {}
with tarfile.open(archive, "r:gz") as bundle:
    for entry in bundle:
        assert entry.isfile() and entry.name.startswith(str(RELATIVE) + "/")
        stream = bundle.extractfile(entry)
        assert stream is not None
        observed[entry.name] = sha256_bytes(stream.read())
assert observed == hashes
write_json(
    PACKET / "failed-reproduction-archive.json",
    {
        "status": "verified_preserved_failed_reproduction",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "interpretation": "All900 were executed; strict aggregate failed on failed-leg seed metadata. Not a successful reproduction.",
        "original_worktree": str(SOURCE_ROOT),
        "original_reproduction": str(RELATIVE),
        "archive": str(archive.relative_to(ROOT)),
        "archive_sha256": sha256_bytes(archive.read_bytes()),
        "archive_bytes": archive.stat().st_size,
        "source_bytes": sum(path.stat().st_size for path in files),
        "files": len(files),
        "file_hashes": hashes,
    },
)
print(f"Preserved and verified {len(files)} failed-playback files in {archive.stat().st_size:,} archive bytes.")
