"""Local fake-provider proof: metadata equality fails closed and SSE bytes pass unchanged."""

import http.client
import json
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from housing.identity import ROOT, write_json

proof = Path(__file__).resolve().parent
profile = json.loads((ROOT / "configs/model_manifest_v4.json").read_bytes())["profiles"][0]
frozen = profile["show"]["parameters"]
received = []
changed = False
chunks = [b'data: {"value":"caf\xc3\xa9"}\n\n', b'data: [DONE]\n\n']


class FakeProvider(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: object) -> None:
        pass

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"]))
        received.append((self.path, body))
        if self.path == "/api/show":
            parameters = "\n".join(reversed(frozen.splitlines()))
            if changed:
                parameters = parameters.replace("0.2", "0.25")
            payload = json.dumps({"parameters": parameters, "unchanged_field": "fixture"}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for block in chunks:
                self.wfile.write(f"{len(block):x}\r\n".encode() + block + b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()


backend = ThreadingHTTPServer(("127.0.0.1", 0), FakeProvider)
threading.Thread(target=backend.serve_forever, daemon=True).start()
with socket.socket() as reserved:
    reserved.bind(("127.0.0.1", 0))
    port = reserved.getsockname()[1]
with (proof / "adapter-fixture.log").open("wb") as log:
    child = subprocess.Popen([sys.executable, "scripts/serve_frozen_ollama.py", "--port", str(port), "--backend-port", str(backend.server_port)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.1):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError("Fixture adapter did not start")
        body = json.dumps({"model": profile["model"]}).encode()
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        client.request("POST", "/api/show", body, {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200
        metadata = json.loads(response.read())
        assert metadata == {"parameters": frozen, "unchanged_field": "fixture"}
        client.close()
        changed = True
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        client.request("POST", "/api/show", body, {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 502
        response.read()
        client.close()
        generation_body = json.dumps({"model": profile["model"], "messages": [{"role": "user", "content": "explicit auxiliary fixture"}], "stream": True}).encode()
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        client.request("POST", "/v1/chat/completions", generation_body, {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200 and response.read() == b"".join(chunks)
        assert received[-1] == ("/v1/chat/completions", generation_body)
        client.close()
        write_json(proof / "adapter-fixture.json", {"status": "verified_auxiliary_transport_fixture", "real_model_calls": 0, "metadata_order_only": True, "changed_temperature_refused": True, "inference_request_bytes_unchanged": True, "chunked_sse_content_bytes_unchanged": True, "scope": "Synthetic local transport test, not a campaign sample"})
        print("Passed: order-only metadata restoration, changed-value rejection and byte-exact streamed request/response forwarding; zero real model calls.")
    finally:
        child.terminate()
        child.wait(timeout=5)
        backend.shutdown()
        backend.server_close()
