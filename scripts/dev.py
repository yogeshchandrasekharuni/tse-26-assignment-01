"""Run the local API and Vite together; Ctrl-C shuts down both owned processes."""

import signal
import subprocess
import sys
import time

from housing.identity import ROOT

commands = [
    [sys.executable, "-m", "uvicorn", "housing.api.app:app", "--host", "127.0.0.1", "--port", "8000"],
    ["npm", "--prefix", "frontend", "run", "dev"],
]
processes: list[subprocess.Popen[bytes]] = []


def stop(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, stop)
print("Housing Evidence: http://127.0.0.1:5173 · local synthetic data", flush=True)
try:
    for command in commands:
        processes.append(subprocess.Popen(command, cwd=ROOT))
    while all(process.poll() is None for process in processes):
        time.sleep(0.25)
    raise SystemExit(
        next((process.returncode or 0 for process in processes if process.poll() is not None), 1)
    )
except KeyboardInterrupt:
    pass
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
