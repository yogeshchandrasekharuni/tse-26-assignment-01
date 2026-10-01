"""The exact reusable execution boundary shared by live capture and offline replay."""

import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import httpx

from housing.contracts.common import FrozenModel, Seed, Sha256
from housing.contracts.errors import HousingError
from housing.contracts.request import AnalysisRequest
from housing.data.store import Snapshot
from housing.identity import ROOT, semantic_hash, sha256_bytes


class ExecutionIdentity(FrozenModel):
    schema_version: Literal["production-boundary-3"]
    inputs: dict[str, Sha256]
    python_version: str
    fast_agent_version: str
    pydantic_version: str
    full_request_sha256: Sha256
    dataset_view_sha256: Sha256
    source_snapshot_sha256: Sha256
    index_sha256: Sha256
    model_digest: Sha256
    seed: Seed


class RunManifest(FrozenModel):
    schema_version: Literal["production-run-3"]
    mode: Literal["live", "replay"]
    identity: ExecutionIdentity
    boundary_sha256: Sha256
    source_capture: str | None


def execution_identity(request: AnalysisRequest, snapshot: Snapshot) -> ExecutionIdentity:
    overlay = ROOT / f"configs/fast-agent-home/model-overlays/housing-v4-s{request.seed}.yaml"
    if not overlay.is_file():
        raise HousingError(
            "MODEL_UNAVAILABLE", "No frozen model profile for the requested seed", "model_profile"
        )
    inputs: list[Path] = [ROOT / "src/housing/identity.py"]
    for part in ("contracts", "data", "tools", "agents", "workflow", "replay"):
        inputs.extend(sorted((ROOT / "src/housing" / part).rglob("*.py")))
    inputs.extend(sorted((ROOT / "prompts/v3").glob("*.md")))
    inputs.extend(
        [
            ROOT / "uv.lock",
            ROOT / "pyproject.toml",
            ROOT / "configs/production-v4.yaml",
            ROOT / "configs/model_manifest_v4.json",
            overlay,
        ]
    )
    model_manifest = json.loads((ROOT / "configs/model_manifest_v4.json").read_bytes())
    name = f"housing-qwen-v4-s{request.seed}:latest"
    tag = next((t for t in model_manifest["tags"]["models"] if t["name"] == name), None)
    if tag is None:
        raise HousingError("MODEL_UNAVAILABLE", "Missing frozen model digest", "model_profile")
    return ExecutionIdentity(
        schema_version="production-boundary-3",
        inputs={str(p.relative_to(ROOT)): sha256_bytes(p.read_bytes()) for p in inputs},
        python_version=platform.python_version(),
        fast_agent_version=version("fast-agent-mcp"),
        pydantic_version=version("pydantic"),
        full_request_sha256=semantic_hash(request),
        dataset_view_sha256=snapshot.view_sha256,
        source_snapshot_sha256=snapshot.source_sha256,
        index_sha256=snapshot.index_sha256,
        model_digest=tag["digest"],
        seed=request.seed,
    )


async def verify_live_model(identity: ExecutionIdentity) -> None:
    frozen = json.loads((ROOT / "configs/model_manifest_v4.json").read_bytes())
    profile = next(p for p in frozen["profiles"] if p["seed"] == identity.seed)
    name = profile["model"]
    try:
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:11434", trust_env=False, timeout=20
        ) as client:
            tags = await client.get("/api/tags")
            tags.raise_for_status()
            current = next((t for t in tags.json()["models"] if t["name"] == name + ":latest"), None)
            show = await client.post("/api/show", json={"model": name})
            show.raise_for_status()
        if (
            current is None
            or current["digest"] != identity.model_digest
            or show.json()["parameters"] != profile["show"]["parameters"]
        ):
            raise HousingError(
                "MODEL_UNAVAILABLE",
                "Local model digest/defaults differ from the frozen profile",
                "model_profile",
            )
    except httpx.HTTPError as error:
        raise HousingError(
            "MODEL_UNAVAILABLE", f"Local inference profile cannot be verified: {error}", "model_profile"
        ) from error
