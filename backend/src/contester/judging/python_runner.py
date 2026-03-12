from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class PythonExecutionStatus(StrEnum):
    SUCCESS = "success"
    RUNTIME_ERROR = "runtime_error"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"


@dataclass(slots=True)
class PythonExecutionResult:
    status: PythonExecutionStatus
    execution_time_ms: int
    stdout: str
    stderr: str


class PythonRunner:
    def execute(
        self,
        *,
        source_code: str,
        input_data: str,
        time_limit_ms: int,
        workspace_dir: Path,
    ) -> PythonExecutionResult:
        source_path = workspace_dir / "solution.py"
        source_path.write_text(source_code, encoding="utf-8")

        command = [sys.executable, "-I", str(source_path.name)]
        started_at = time.monotonic()

        try:
            completed = subprocess.run(
                command,
                input=input_data,
                capture_output=True,
                text=True,
                cwd=workspace_dir,
                timeout=time_limit_ms / 1000,
                env={
                    **os.environ,
                    "PYTHONIOENCODING": "utf-8",
                },
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            execution_time_ms = max(int((time.monotonic() - started_at) * 1000), time_limit_ms)
            return PythonExecutionResult(
                status=PythonExecutionStatus.TIME_LIMIT_EXCEEDED,
                execution_time_ms=execution_time_ms,
                stdout=error.stdout or "",
                stderr=error.stderr or "",
            )

        execution_time_ms = int((time.monotonic() - started_at) * 1000)

        if completed.returncode != 0:
            return PythonExecutionResult(
                status=PythonExecutionStatus.RUNTIME_ERROR,
                execution_time_ms=execution_time_ms,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

        return PythonExecutionResult(
            status=PythonExecutionStatus.SUCCESS,
            execution_time_ms=execution_time_ms,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )