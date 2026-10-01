"""Generate the browser contract from actual strict backend models."""

import argparse
import json

from housing.api.app import app
from housing.api.models import ClientContracts
from housing.identity import ROOT, write_json

parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
for name, value in (
    ("client.schema.json", ClientContracts.model_json_schema()),
    ("openapi.json", app.openapi()),
):
    target = ROOT / "schemas" / name
    if args.check:
        if not target.is_file() or json.loads(target.read_bytes()) != value:
            raise SystemExit(f"Stale backend schema: {target.relative_to(ROOT)}; run make contracts")
    else:
        write_json(target, value)
print(
    "Strict backend/client schemas verified" if args.check else "Generated strict client schema and OpenAPI"
)
