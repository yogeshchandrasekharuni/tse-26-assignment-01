"""Local metadata-order adapter v1; inference request/response bytes pass through unchanged."""

import argparse
import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from housing.identity import ROOT, sha256_bytes
from housing.runtime_compat import frozen_parameter_order

HOP_HEADERS = frozenset(
    {"connection", "keep-alive", "transfer-encoding", "proxy-connection", "te", "trailer", "upgrade"}
)
PATHS = frozenset(
    {
        "/api/version",
        "/api/tags",
        "/api/show",
        "/api/ps",
        "/api/generate",
        "/api/chat",
        "/v1/models",
        "/v1/chat/completions",
    }
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11434)
    parser.add_argument("--backend-port", type=int, default=11435)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "configs/model_manifest_v4.json").read_bytes())
    frozen = {p["model"]: p["show"]["parameters"] for p in manifest["profiles"]}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *values: object) -> None:
            return

        def forward(self) -> None:
            if self.path not in PATHS:
                self.send_error(403, "Endpoint outside the frozen local experiment")
                return
            size = int(self.headers.get("Content-Length", "0"))
            if size < 0 or size > 16 * 1024 * 1024 or self.headers.get("Transfer-Encoding"):
                self.send_error(400, "Unsupported request framing")
                return
            body = self.rfile.read(size)
            payload = json.loads(body) if body else {}
            model = str(payload.get("model", "")).removesuffix(":latest")
            if self.command == "POST" and model not in frozen:
                self.send_error(403, "Model outside the frozen local experiment")
                return
            headers = {
                key: value for key, value in self.headers.items() if key.lower() not in HOP_HEADERS | {"host"}
            }
            backend = http.client.HTTPConnection("127.0.0.1", args.backend_port, timeout=650)
            sent = False
            try:
                backend.request(self.command, self.path, body=body or None, headers=headers)
                response = backend.getresponse()
                rewritten = None
                if self.path == "/api/show" and response.status == 200:
                    metadata = json.loads(response.read())
                    original = metadata["parameters"]
                    metadata["parameters"] = frozen_parameter_order(original, frozen[model])
                    rewritten = json.dumps(metadata, separators=(",", ":")).encode()
                    print(
                        json.dumps(
                            {
                                "event": "metadata_order_verified",
                                "model": model,
                                "raw_parameter_sha256": sha256_bytes(original.encode()),
                                "frozen_parameter_sha256": sha256_bytes(frozen[model].encode()),
                                "order_restored": original != frozen[model],
                            }
                        ),
                        flush=True,
                    )
                self.send_response(response.status, response.reason)
                for key, value in response.getheaders():
                    if key.lower() not in HOP_HEADERS and not (
                        rewritten is not None and key.lower() == "content-length"
                    ):
                        self.send_header(key, value)
                if rewritten is not None:
                    self.send_header("Content-Length", str(len(rewritten)))
                self.send_header("Connection", "close")
                self.end_headers()
                sent = True
                if rewritten is not None:
                    self.wfile.write(rewritten)
                else:
                    while block := response.read1(65536):
                        self.wfile.write(block)
                        self.wfile.flush()
            except BrokenPipeError, ConnectionResetError:
                pass
            except (OSError, ValueError, KeyError, http.client.HTTPException) as error:
                print(
                    json.dumps(
                        {"event": "adapter_error", "type": type(error).__name__, "message": str(error)}
                    ),
                    flush=True,
                )
                if not sent:
                    self.send_error(502, "Provider metadata or transport verification failed")
            finally:
                backend.close()
                self.close_connection = True

        do_GET = forward
        do_POST = forward

    print(
        json.dumps(
            {
                "event": "adapter_started",
                "revision": "ollama-metadata-order-1",
                "listen": f"127.0.0.1:{args.port}",
                "backend": f"127.0.0.1:{args.backend_port}",
                "scope": "Only /api/show parameter line order may change after exact key/value equality; inference bytes unchanged",
            }
        ),
        flush=True,
    )
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
