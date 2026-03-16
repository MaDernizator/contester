#!/bin/sh
set -eu

exec python - <<'PY'
import os
import signal
import subprocess
import sys
import time

worker_processes_raw = os.environ.get("WORKER_PROCESSES", "1").strip()

try:
    worker_processes = int(worker_processes_raw)
except ValueError as error:
    raise SystemExit("WORKER_PROCESSES must be an integer.") from error

if worker_processes < 1:
    raise SystemExit("WORKER_PROCESSES must be at least 1.")

command = ["flask", "--app", "wsgi", "run-judge-worker"]
children: list[subprocess.Popen[str]] = []
shutting_down = False


def stop_children(exit_code: int) -> None:
    global shutting_down
    if shutting_down:
        raise SystemExit(exit_code)

    shutting_down = True

    for child in children:
        if child.poll() is None:
            child.terminate()

    deadline = time.time() + 10

    for child in children:
        if child.poll() is not None:
            continue

        remaining = max(deadline - time.time(), 0.0)
        try:
            child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            child.kill()

    raise SystemExit(exit_code)


def handle_signal(signum, frame) -> None:
    stop_children(0)


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

for index in range(worker_processes):
    child = subprocess.Popen(command, text=True)
    children.append(child)
    print(f"Started judge worker process {index + 1}/{worker_processes} with pid={child.pid}", flush=True)

while True:
    for child in children:
        return_code = child.poll()
        if return_code is not None:
            print(
                f"Judge worker process pid={child.pid} exited with code {return_code}. Stopping the group.",
                flush=True,
            )
            stop_children(return_code if return_code != 0 else 1)

    time.sleep(1)
PY