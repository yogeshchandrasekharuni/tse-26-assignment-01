"""Project immutable live captures into Langfuse's supported OTLP/HTTP JSON protocol.

No model invocation, replay execution, shared tracer provider or global instrumentation.
Historical timing comes from recorded provider telemetry. Point events have zero duration.
"""

import json
import re
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr

from housing.identity import ROOT, canonical_json, semantic_hash, sha256_bytes
from housing.replay.capture import Cassette
from housing.reporting.usage import response_usage

EXPORT_VERSION: Literal["housing-langfuse-1"] = "housing-langfuse-1"
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
ROLES = {"orchestrator", "price", "supply", "region", "reviewer", "composer"}


class Span(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    key: str
    name: str
    kind: Literal["agent", "generation", "tool", "event", "evaluator", "guardrail"]
    parent_key: str | None
    start_ns: int
    end_ns: int
    attributes: dict[str, str | int | bool | list[str]]
    error: bool = False
    link_keys: tuple[str, ...] = ()


class CaptureProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["housing-langfuse-1"] = EXPORT_VERSION
    run_path: str
    run_id: str
    trace_id: str
    evidence_scope: str
    exporter_sha256: str
    artifact_hashes: dict[str, str]
    spans: list[Span]

    def span_id(self, key: str) -> str:
        return semantic_hash([EXPORT_VERSION, self.run_path, key])[:16]

    def otlp(self) -> dict[str, Any]:
        def value(item: str | int | bool | list[str]) -> dict[str, Any]:
            if type(item) is bool:
                return {"boolValue": item}
            if type(item) is int:
                return {"intValue": str(item)}
            if isinstance(item, list):
                return {"arrayValue": {"values": [{"stringValue": entry} for entry in item]}}
            return {"stringValue": item}

        spans = []
        for span in self.spans:
            row: dict[str, Any] = {
                "traceId": self.trace_id,
                "spanId": self.span_id(span.key),
                "name": span.name,
                "kind": 1,
                "startTimeUnixNano": str(span.start_ns),
                "endTimeUnixNano": str(span.end_ns),
                "attributes": [
                    {"key": key, "value": value(item)}
                    for key, item in sorted(
                        {**span.attributes, "langfuse.observation.type": span.kind}.items()
                    )
                ],
                "status": {"code": 2 if span.error else 0},
                "links": [{"traceId": self.trace_id, "spanId": self.span_id(key)} for key in span.link_keys],
            }
            if span.parent_key:
                row["parentSpanId"] = self.span_id(span.parent_key)
            spans.append(row)
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "housing-tse"}},
                            {"key": "service.version", "value": {"stringValue": EXPORT_VERSION}},
                        ]
                    },
                    "scopeSpans": [{"scope": {"name": "housing.capture-export"}, "spans": spans}],
                }
            ]
        }


def unix_ns(timestamp: str) -> int:
    moment = datetime.fromisoformat(timestamp)
    if moment.tzinfo is None:
        raise ValueError("Capture timestamps must carry a timezone")
    delta = moment - EPOCH
    return (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000


def decimal_ns(value: object, multiplier: int) -> int:
    number = Decimal(str(value)) * multiplier
    if not number.is_finite() or number < 0:
        raise ValueError("Invalid provider timing")
    return int(number.to_integral_value(rounding=ROUND_HALF_EVEN))


def project_capture(directory: Path) -> CaptureProjection:
    directory = directory.resolve()
    registries = (ROOT / "artifacts/traces", ROOT / "artifacts/campaigns", ROOT / "artifacts/runtime/web")
    if not any(directory.is_relative_to(path.resolve()) for path in registries):
        raise ValueError("Export requires a registered local capture")
    hashes: dict[str, str] = {}

    def read(name: str) -> Any:
        path = directory / name
        data = path.read_bytes()
        hashes[str(path.relative_to(ROOT))] = sha256_bytes(data)
        return json.loads(data)

    terminal = read("terminal.json")  # Written last: active runs are never exported.
    manifest = read("run-manifest.json")
    if manifest["mode"] != "live":
        raise ValueError("Export live captures only; replay usage and timing are historical")
    if semantic_hash(manifest["identity"]) != manifest["boundary_sha256"]:
        raise ValueError("Run identity differs from the captured boundary")
    request = read("request.json")
    trace_path = directory / "trace.jsonl"
    raw_trace = trace_path.read_bytes()
    hashes[str(trace_path.relative_to(ROOT))] = sha256_bytes(raw_trace)
    events = [json.loads(line) for line in raw_trace.splitlines()]
    if not events or events[-1]["event"] not in {"RUN_COMPLETED", "RUN_FAILED"}:
        raise ValueError("Capture has no terminal workflow event")
    run_id = events[0]["run_id"]
    for sequence, event in enumerate(events):
        if (
            event["sequence"] != sequence
            or event["run_id"] != run_id
            or event["mode"] != "live"
            or semantic_hash(event["payload"]) != event["payload_sha256"]
        ):
            raise ValueError("Workflow event integrity differs")
    start, end = unix_ns(events[0]["timestamp_utc"]), unix_ns(events[-1]["timestamp_utc"])
    if end < start or any(
        unix_ns(a["timestamp_utc"]) > unix_ns(b["timestamp_utc"]) for a, b in pairwise(events)
    ):
        raise ValueError("Capture wall clock is not monotonic; timing requires review")
    scope = (
        "auxiliary_index_omission"
        if events[0]["payload"].get("injected_index_omissions")
        else "headline"
        if "headline-live-v1" in directory.parts
        else "pilot"
        if "pilot-live-v1" in directory.parts
        else "interactive_live"
        if directory.is_relative_to(ROOT / "artifacts/runtime/web")
        else "development_smoke"
    )
    common: dict[str, str | int | bool | list[str]] = {
        "langfuse.environment": "housing-local",
        "langfuse.trace.name": f"Orchestrator · {run_id}",
        "langfuse.trace.tags": ["synthetic", "live-capture", scope],
        "langfuse.trace.public": False,
        "langfuse.observation.metadata.run_id": run_id,
        "langfuse.observation.metadata.evidence_scope": scope,
        "langfuse.observation.metadata.capture_path": str(directory.relative_to(ROOT)),
        "langfuse.observation.metadata.export_version": EXPORT_VERSION,
        "langfuse.observation.metadata.exporter_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "langfuse.observation.metadata.execution_status": terminal["status"],
        "langfuse.observation.metadata.dataset_view_sha256": events[0]["dataset_view_sha256"],
        "langfuse.observation.metadata.query_sha256": events[0]["query_sha256"],
        "langfuse.observation.metadata.boundary_sha256": manifest["boundary_sha256"],
        "langfuse.observation.metadata.requested_seed": request["seed"],
        "langfuse.observation.metadata.timing_note": "Historical live capture; event spans have zero duration",
        "session.id": next(
            (part for part in directory.parts if re.fullmatch(r"MR\d{2}-b\d{3}-s\d+", part)),
            run_id,
        ),
    }
    if "campaigns" in directory.parts:
        common["langfuse.observation.metadata.campaign_id"] = directory.parts[
            directory.parts.index("campaigns") + 1
        ]
        for part in directory.parts:
            if match := re.fullmatch(r"(MR\d{2})-(b\d{3})-s\d+", part):
                common["langfuse.observation.metadata.mr_id"] = match[1]
                common["langfuse.observation.metadata.base_id"] = match[2]
        if "runs" in directory.parts:
            common["langfuse.observation.metadata.leg"] = directory.parts[directory.parts.index("runs") - 1]
    failure = terminal["status"] == "failed"
    root_output = {"terminal": terminal}
    if (directory / "output.json").is_file():
        analysis = read("output.json")
        if semantic_hash(analysis) != events[-1]["payload"].get("output_sha256"):
            raise ValueError("Published analysis differs from the terminal workflow hash")
        root_output["analysis"] = analysis
    spans = [
        Span(
            key="orchestrator",
            name="Orchestrator",
            kind="agent",
            parent_key=None,
            start_ns=start,
            end_ns=end,
            attributes={
                **common,
                "langfuse.observation.input": canonical_json(request),
                "langfuse.observation.output": canonical_json(root_output),
                "langfuse.observation.level": "ERROR" if failure else "DEFAULT",
            },
            error=failure,
        )
    ]
    cassette_paths = sorted((directory / "cassettes").glob("*.json"))
    expected = terminal["cassette_hashes"]
    if set(expected) != {path.stem for path in cassette_paths}:
        raise ValueError("Cassette inventory differs from terminal evidence")
    input_names = {path.stem.removesuffix(".input") for path in (directory / "model").glob("*.input.json")}
    response_names = {
        path.stem.removesuffix(".response") for path in (directory / "model").glob("*.response.json")
    }
    for path in sorted((directory / "model").glob("*.json")):
        read(f"model/{path.name}")
    spans[0].attributes["langfuse.observation.metadata.recorded_inputs_without_response"] = len(
        input_names - response_names
    )
    spans[0].attributes["langfuse.observation.metadata.orphan_input_sequences"] = sorted(
        input_names - response_names
    )
    pending: list[tuple[str, str, int]] = []
    assignments: dict[int, str] = {}
    for sequence, path in enumerate(cassette_paths):
        packet = Cassette.model_validate_json(canonical_json(read(f"cassettes/{path.name}")))
        if packet.sequence != sequence or hashes[str(path.relative_to(ROOT))] != expected[path.stem]:
            raise ValueError("Cassette sequence or byte hash differs")
        packet.verify(packet.input, manifest["boundary_sha256"])
        raw_input = read(f"model/{sequence:03d}.input.json")
        raw_response = read(f"model/{sequence:03d}.response.json")
        if semantic_hash(raw_input) != packet.raw_input_sha256:
            raise ValueError("Model input differs from the cassette")
        if semantic_hash(raw_response) != semantic_hash(packet.response):
            raise ValueError("Model response differs from the cassette")
        role = str(raw_input["agent"]).split("[", 1)[0]
        if role not in ROLES:
            raise ValueError("Unrecognized captured role")
        iteration = raw_input["context"]["iteration"]
        usage = response_usage(raw_response)
        attempt_blocks = raw_response.get("channels", {}).get("fast-agent-usage", [])
        attempts = [
            attempt
            for block in attempt_blocks
            for attempt in json.loads(block["text"], parse_float=Decimal)["provider_attempts"]
        ]
        timed = [
            a
            for a in attempts
            if a.get("timestamp") is not None and a.get("timing", {}).get("duration_ms") is not None
        ]
        if timed:
            finish = max(decimal_ns(a["timestamp"], 1_000_000_000) for a in timed)
            begin = min(
                decimal_ns(a["timestamp"], 1_000_000_000) - decimal_ns(a["timing"]["duration_ms"], 1_000_000)
                for a in timed
            )
            timing_basis = "provider_attempt_wall_end_minus_reported_duration"
            if not start <= begin <= finish <= end:
                raise ValueError("Provider timing lies outside the workflow; review clock alignment")
        else:
            # Missing telemetry is explicit. No invented model latency.
            finish = begin = start
            timing_basis = "unknown; point at run start, not a measured latency"
        parent = "orchestrator"
        if role != "orchestrator":
            if not pending or pending[0][0] != role:
                raise ValueError("Child role does not match preserved native delegation order")
            _, native_call_id, parent_sequence = pending.pop(0)
            parent = f"agent-{sequence:03d}"
            spans.append(
                Span(
                    key=parent,
                    name=f"{role.title()} · pass {iteration + 1}",
                    kind="agent",
                    parent_key="orchestrator",
                    start_ns=begin,
                    end_ns=finish,
                    attributes={
                        **common,
                        "langfuse.observation.metadata.native_tool_call_id": native_call_id,
                        "langfuse.observation.metadata.delegating_model_sequence": parent_sequence,
                        "langfuse.observation.metadata.iteration": iteration,
                    },
                )
            )
        generation_key = f"generation-{sequence:03d}"
        attrs: dict[str, str | int | bool | list[str]] = {
            **common,
            "langfuse.observation.input": canonical_json(raw_input),
            "langfuse.observation.output": canonical_json(raw_response),
            "langfuse.observation.model.name": str(attempts[-1].get("model") or raw_input["model_profile"])
            if attempts
            else raw_input["model_profile"],
            "langfuse.observation.metadata.model_profile": raw_input["model_profile"],
            "langfuse.observation.metadata.effective_seed": raw_input["effective_seed"],
            "langfuse.observation.metadata.role_schema_sha256": raw_input["role_schema_sha256"],
            "langfuse.observation.metadata.prompt_bundle_sha256": raw_input["prompt_bundle_sha256"],
            "langfuse.observation.metadata.role": role,
            "langfuse.observation.metadata.iteration": iteration,
            "langfuse.observation.metadata.model_sequence": sequence,
            "langfuse.observation.metadata.timing_basis": timing_basis,
            "langfuse.observation.metadata.provider_telemetry": canonical_json(usage),
        }
        tokens = {
            label: usage[field]["sum_reported"]
            for label, field in (("input", "prompt_total"), ("output", "completion_total"))
            if usage[field]["records_without_value"] == 0 and usage[field]["sum_reported"] is not None
        }
        if tokens:
            attrs["langfuse.observation.usage_details"] = canonical_json(tokens)
        spans.append(
            Span(
                key=generation_key,
                name=f"{sequence:03d} · {role}",
                kind="generation",
                parent_key=parent,
                start_ns=begin,
                end_ns=finish,
                attributes=attrs,
            )
        )
        if role == "orchestrator":
            for call_id in packet.response_tool_call_order:
                name = raw_response["tool_calls"][call_id]["params"]["name"]
                if name.startswith("agent__"):
                    pending.append((name.removeprefix("agent__"), call_id, sequence))
        else:
            # The latest completed call of this role/pass owns its following role events.
            for event in events:
                when = unix_ns(event["timestamp_utc"])
                if event["actor"] == role and event["iteration"] == iteration and when >= finish:
                    assignments[event["sequence"]] = parent
    by_key = {span.key: span for span in spans}
    for event in events:
        sequence = event["sequence"]
        when = unix_ns(event["timestamp_utc"])
        parent = assignments.get(sequence, "orchestrator")
        if parent != "orchestrator":
            by_key[parent].end_ns = max(by_key[parent].end_ns, when)
        invalid = event["payload"].get("valid") is False or event["event"] == "RUN_FAILED"
        if invalid and parent != "orchestrator":
            by_key[parent].error = True
            by_key[parent].attributes["langfuse.observation.level"] = "ERROR"
            generation = by_key[parent.replace("agent-", "generation-")]
            generation.error = True
            generation.attributes["langfuse.observation.level"] = "ERROR"
        kind: Literal["tool", "event", "evaluator", "guardrail"] = (
            "tool"
            if event["event"] in {"TOOL_COMPLETED", "SELECTION_COMPLETED", "AGGREGATE_COMPLETED"}
            else "evaluator"
            if event["event"] == "REVIEW_DECIDED"
            else "guardrail"
            if invalid or event["event"].startswith("SCHEMA_REPAIR")
            else "event"
        )
        cause = event["parent_event_sequence"]
        spans.append(
            Span(
                key=f"event-{sequence:03d}",
                name=f"{sequence:02d} · {event['event']} · {event['actor']}",
                kind=kind,
                parent_key=parent,
                start_ns=when,
                end_ns=when,
                attributes={
                    **common,
                    "langfuse.observation.input": canonical_json(
                        {"actor": event["actor"], "iteration": event["iteration"]}
                    ),
                    "langfuse.observation.output": canonical_json(
                        {k: v for k, v in event["payload"].items() if k != "traceback"}
                    ),
                    "langfuse.observation.level": "ERROR" if invalid else "DEFAULT",
                    "langfuse.observation.metadata.event_sequence": sequence,
                    "langfuse.observation.metadata.iteration": event["iteration"],
                    "langfuse.observation.metadata.payload_sha256": event["payload_sha256"],
                    "langfuse.observation.metadata.timing_basis": "recorded_event_point; operation duration unavailable",
                },
                error=invalid,
                link_keys=(f"event-{cause:03d}",) if cause is not None else (),
            )
        )
    return CaptureProjection(
        run_path=str(directory.relative_to(ROOT)),
        run_id=run_id,
        trace_id=semantic_hash(
            [EXPORT_VERSION, str(directory.relative_to(ROOT)), manifest["boundary_sha256"]]
        )[:32],
        evidence_scope=scope,
        exporter_sha256=sha256_bytes(Path(__file__).read_bytes()),
        artifact_hashes=hashes,
        spans=spans,
    )


class LocalLangfuse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    base_url: str
    public_key: SecretStr
    secret_key: SecretStr
    project_id: str

    @classmethod
    def from_file(cls, path: Path) -> LocalLangfuse:
        values = dict(
            line.strip().split("=", 1)
            for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        url = values["LANGFUSE_BASE_URL"]
        parsed = urlsplit(url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.port != 19300
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("This integration is authorized only for local Langfuse on port19300")
        return cls(
            base_url=url.rstrip("/"),
            public_key=SecretStr(values["LANGFUSE_PUBLIC_KEY"]),
            secret_key=SecretStr(values["LANGFUSE_SECRET_KEY"]),
            project_id=values["LANGFUSE_PROJECT_ID"],
        )

    def client(self, transport: httpx.BaseTransport | None = None) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            auth=httpx.BasicAuth(self.public_key.get_secret_value(), self.secret_key.get_secret_value()),
            headers={"x-langfuse-ingestion-version": "4"},
            trust_env=False,
            follow_redirects=False,
            timeout=30,
            transport=transport,
        )


def send_projection(projection: CaptureProjection, client: httpx.Client) -> None:
    response = client.post("/api/public/otel/v1/traces", json=projection.otlp())
    if response.status_code != 200:
        raise ValueError(f"Langfuse ingestion returned HTTP{response.status_code}; export not acknowledged")
    body = response.json()
    partial = body.get("partialSuccess", body.get("partial_success", {}))
    if (
        int(partial.get("rejectedSpans", partial.get("rejected_spans", 0)))
        or partial.get("errorMessage")
        or partial.get("error_message")
    ):
        raise ValueError("Langfuse reported partial ingestion; export not acknowledged")


def observed_span_ids(projection: CaptureProjection, client: httpx.Client) -> set[str]:
    root = projection.spans[0]
    params: dict[str, str | int] = {
        "traceId": projection.trace_id,
        "limit": 100,
        "fields": "core,basic",
        "fromStartTime": datetime.fromtimestamp(root.start_ns // 1_000_000_000, UTC).isoformat(),
        "toStartTime": datetime.fromtimestamp(root.end_ns // 1_000_000_000 + 1, UTC).isoformat(),
    }
    observed: set[str] = set()
    cursors: set[str] = set()
    for _ in range(10):
        response = client.get("/api/public/v2/observations", params=params)
        response.raise_for_status()
        body = response.json()
        observed.update(str(row["id"]) for row in body["data"] if row["traceId"] == projection.trace_id)
        cursor = body.get("meta", {}).get("cursor")
        if not cursor:
            return observed
        if cursor in cursors:
            raise ValueError("Langfuse repeated an observation page cursor")
        cursors.add(cursor)
        params["cursor"] = cursor
    raise ValueError("Observation readback exceeded the bounded page limit")
