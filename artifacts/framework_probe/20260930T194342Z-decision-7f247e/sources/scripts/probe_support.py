"""Framework spike support. Evidence here is never a housing campaign result."""

import hashlib
import json
import socket
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import httpx


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


class Evidence:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=False)
        self.events: list[dict] = []
        self.lock = threading.Lock()

    def log(self, event: str, **payload: object) -> None:
        with self.lock:
            record = {"sequence": len(self.events), "timestamp_utc": datetime.now(UTC).isoformat(),
                      "event": event, **payload}
            self.events.append(record)
            with (self.directory / "events.jsonl").open("a") as f:
                f.write(canonical(record) + "\n")


class RecordingProxy:
    """Transparent localhost audit proxy; never changes model requests or responses."""
    def __init__(self, evidence: Evidence):
        self.evidence = evidence
        self.requests: list[dict] = []
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                pass

            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers["Content-Length"]))
                request = json.loads(body)
                with owner.lock:
                    index = len(owner.requests)
                    owner.requests.append(request)
                prefix = f"wire/{index:04d}"
                write_json(evidence.directory / f"{prefix}-request.json", request)
                evidence.log("PROVIDER_REQUEST", index=index, model=request.get("model"),
                             request_sha256=digest(request))
                start = time.monotonic()
                try:
                    response = httpx.post("http://127.0.0.1:11434" + self.path,
                                          content=body, headers={"Content-Type": "application/json",
                                                                 "Authorization": "Bearer ollama"},
                                          timeout=90, trust_env=False)
                    (evidence.directory / f"{prefix}-response.txt").write_bytes(response.content)
                    evidence.log("PROVIDER_RESPONSE", index=index, http_status=response.status_code,
                                 elapsed_seconds=round(time.monotonic() - start, 6),
                                 response_sha256=hashlib.sha256(response.content).hexdigest())
                    self.send_response(response.status_code)
                    self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                    self.send_header("Content-Length", str(len(response.content)))
                    self.end_headers()
                    self.wfile.write(response.content)
                except Exception as error:
                    evidence.log("PROVIDER_ERROR", index=index, error=repr(error))
                    self.send_error(502, "Local inference transport failed")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/v1"


def match_cassette(directory: Path, basis: dict) -> dict:
    path = directory / f"{digest(basis)}.json"
    if not path.exists():
        raise ValueError("REPLAY_MISS: exact decision cassette absent")
    cassette = json.loads(path.read_text())
    if cassette["origin"] != "live_captured" or cassette["key_basis"] != basis:
        raise ValueError("REPLAY_MISS: lineage or semantic inputs differ")
    response_hash = hashlib.sha256(cassette["raw_response_text"].encode()).hexdigest()
    if response_hash != cassette["raw_response_sha256"]:
        raise ValueError("REPLAY_MISS: corrupt response")
    return cassette


@contextmanager
def deny_network():
    attempts: list[str] = []

    def denied(*args, **kwargs):
        attempts.append(repr(args[1:] if len(args) > 1 else args))
        raise OSError("OFFLINE: network connections prohibited")

    with patch.object(socket.socket, "connect", denied), patch.object(socket.socket, "connect_ex", denied), \
            patch.object(socket, "create_connection", denied):
        yield attempts
