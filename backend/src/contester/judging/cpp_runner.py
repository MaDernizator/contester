from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class CppCompilationStatus(StrEnum):
    SUCCESS = "success"
    COMPILATION_ERROR = "compilation_error"
    COMPILER_NOT_AVAILABLE = "compiler_not_available"
    INTERNAL_ERROR = "internal_error"


class CppExecutionStatus(StrEnum):
    SUCCESS = "success"
    RUNTIME_ERROR = "runtime_error"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"


@dataclass(slots=True)
class CppCompilationResult:
    status: CppCompilationStatus
    compile_time_ms: int
    stdout: str
    stderr: str
    binary_path: Path | None


@dataclass(slots=True)
class CppExecutionResult:
    status: CppExecutionStatus
    execution_time_ms: int
    stdout: str
    stderr: str


class CppRunner:
    def compile(
        self,
        *,
        source_code: str,
        workspace_dir: Path,
        compiler: str,
        timeout_sec: int,
    ) -> CppCompilationResult:
        source_path = workspace_dir / "solution.cpp"
        binary_name = "solution.exe" if os.name == "nt" else "solution"
        binary_path = workspace_dir / binary_name

        source_path.write_text(source_code, encoding="utf-8")

        command = [
            compiler,
            "-std=c++17",
            "-O2",
            "-o",
            str(binary_path),
            str(source_path),
        ]

        started_at = time.monotonic()

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=workspace_dir,
                timeout=timeout_sec,
                env={
                    **os.environ,
                    "LC_ALL": "C",
                },
                check=False,
            )
        except FileNotFoundError as error:
            compile_time_ms = int((time.monotonic() - started_at) * 1000)
            return CppCompilationResult(
                status=CppCompilationStatus.COMPILER_NOT_AVAILABLE,
                compile_time_ms=compile_time_ms,
                stdout="",
                stderr=str(error),
                binary_path=None,
            )
        except subprocess.TimeoutExpired as error:
            compile_time_ms = int((time.monotonic() - started_at) * 1000)
            return CppCompilationResult(
                status=CppCompilationStatus.COMPILATION_ERROR,
                compile_time_ms=compile_time_ms,
                stdout=error.stdout or "",
                stderr=(error.stderr or "") + "\nCompilation timed out.",
                binary_path=None,
            )
        except OSError as error:
            compile_time_ms = int((time.monotonic() - started_at) * 1000)
            return CppCompilationResult(
                status=CppCompilationStatus.INTERNAL_ERROR,
                compile_time_ms=compile_time_ms,
                stdout="",
                stderr=str(error),
                binary_path=None,
            )

        compile_time_ms = int((time.monotonic() - started_at) * 1000)

        if completed.returncode != 0:
            return CppCompilationResult(
                status=CppCompilationStatus.COMPILATION_ERROR,
                compile_time_ms=compile_time_ms,
                stdout=completed.stdout,
                stderr=completed.stderr,
                binary_path=None,
            )

        return CppCompilationResult(
            status=CppCompilationStatus.SUCCESS,
            compile_time_ms=compile_time_ms,
            stdout=completed.stdout,
            stderr=completed.stderr,
            binary_path=binary_path,
        )

    def execute(
        self,
        *,
        binary_path: Path,
        input_data: str,
        time_limit_ms: int,
        workspace_dir: Path,
    ) -> CppExecutionResult:
        started_at = time.monotonic()

        try:
            completed = subprocess.run(
                [str(binary_path)],
                input=input_data,
                capture_output=True,
                text=True,
                cwd=workspace_dir,
                timeout=time_limit_ms / 1000,
                env={
                    **os.environ,
                    "LC_ALL": "C",
                },
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            execution_time_ms = max(int((time.monotonic() - started_at) * 1000), time_limit_ms)
            return CppExecutionResult(
                status=CppExecutionStatus.TIME_LIMIT_EXCEEDED,
                execution_time_ms=execution_time_ms,
                stdout=error.stdout or "",
                stderr=error.stderr or "",
            )

        execution_time_ms = int((time.monotonic() - started_at) * 1000)

        if completed.returncode != 0:
            return CppExecutionResult(
                status=CppExecutionStatus.RUNTIME_ERROR,
                execution_time_ms=execution_time_ms,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

        return CppExecutionResult(
            status=CppExecutionStatus.SUCCESS,
            execution_time_ms=execution_time_ms,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )