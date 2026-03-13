from __future__ import annotations

import os
import subprocess
import time
import uuid
from pathlib import Path

from contester.judging.cpp_runner import (
    CppCompilationResult,
    CppCompilationStatus,
    CppExecutionResult,
    CppExecutionStatus,
)
from contester.judging.python_runner import (
    PythonExecutionResult,
    PythonExecutionStatus,
)


def _timeout_stream_to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


class DockerRunner:
    def __init__(self, *, image: str, docker_binary: str = "docker") -> None:
        self.image = image
        self.docker_binary = docker_binary

    def execute_python(
        self,
        *,
        source_code: str,
        input_data: str,
        time_limit_ms: int,
        workspace_dir: Path,
        memory_limit_mb: int,
    ) -> PythonExecutionResult:
        source_path = workspace_dir / "solution.py"
        source_path.write_text(source_code, encoding="utf-8")

        container_name = self._make_container_name("python")
        command = self._build_docker_run_command(
            workspace_dir=workspace_dir,
            container_name=container_name,
            memory_limit_mb=max(memory_limit_mb, 128),
        ) + [
            self.image,
            "python3",
            "-I",
            "/workspace/solution.py",
        ]

        started_at = time.monotonic()

        try:
            completed = self._run_command(
                command=command,
                timeout_sec=time_limit_ms / 1000,
                input_data=input_data,
                container_name=container_name,
            )
        except subprocess.TimeoutExpired as error:
            execution_time_ms = max(int((time.monotonic() - started_at) * 1000), time_limit_ms)
            return PythonExecutionResult(
                status=PythonExecutionStatus.TIME_LIMIT_EXCEEDED,
                execution_time_ms=execution_time_ms,
                stdout=_timeout_stream_to_text(error.stdout),
                stderr=_timeout_stream_to_text(error.stderr),
            )

        execution_time_ms = int((time.monotonic() - started_at) * 1000)

        if completed.returncode == 125:
            raise RuntimeError(completed.stderr.strip() or "Docker execution failed.")

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

    def compile_cpp(
        self,
        *,
        source_code: str,
        workspace_dir: Path,
        compiler: str,
        timeout_sec: int,
        memory_limit_mb: int,
    ) -> CppCompilationResult:
        source_path = workspace_dir / "solution.cpp"
        binary_path = workspace_dir / "solution"

        source_path.write_text(source_code, encoding="utf-8")

        container_name = self._make_container_name("cpp-compile")
        command = self._build_docker_run_command(
            workspace_dir=workspace_dir,
            container_name=container_name,
            memory_limit_mb=max(memory_limit_mb * 2, 256),
        ) + [
            self.image,
            compiler,
            "-std=c++17",
            "-O2",
            "-o",
            "/workspace/solution",
            "/workspace/solution.cpp",
        ]

        started_at = time.monotonic()

        try:
            completed = self._run_command(
                command=command,
                timeout_sec=timeout_sec,
                input_data=None,
                container_name=container_name,
            )
        except subprocess.TimeoutExpired as error:
            compile_time_ms = int((time.monotonic() - started_at) * 1000)
            return CppCompilationResult(
                status=CppCompilationStatus.COMPILATION_ERROR,
                compile_time_ms=compile_time_ms,
                stdout=_timeout_stream_to_text(error.stdout),
                stderr=_timeout_stream_to_text(error.stderr) + "\nCompilation timed out.",
                binary_path=None,
            )

        compile_time_ms = int((time.monotonic() - started_at) * 1000)

        if completed.returncode == 125:
            return CppCompilationResult(
                status=CppCompilationStatus.INTERNAL_ERROR,
                compile_time_ms=compile_time_ms,
                stdout=completed.stdout,
                stderr=completed.stderr,
                binary_path=None,
            )

        if completed.returncode != 0:
            return CppCompilationResult(
                status=CppCompilationStatus.COMPILATION_ERROR,
                compile_time_ms=compile_time_ms,
                stdout=completed.stdout,
                stderr=completed.stderr,
                binary_path=None,
            )

        if not binary_path.exists():
            return CppCompilationResult(
                status=CppCompilationStatus.INTERNAL_ERROR,
                compile_time_ms=compile_time_ms,
                stdout=completed.stdout,
                stderr="Compilation succeeded but output binary was not found.",
                binary_path=None,
            )

        return CppCompilationResult(
            status=CppCompilationStatus.SUCCESS,
            compile_time_ms=compile_time_ms,
            stdout=completed.stdout,
            stderr=completed.stderr,
            binary_path=binary_path,
        )

    def execute_cpp(
        self,
        *,
        binary_path: Path,
        input_data: str,
        time_limit_ms: int,
        workspace_dir: Path,
        memory_limit_mb: int,
    ) -> CppExecutionResult:
        container_name = self._make_container_name("cpp-run")
        command = self._build_docker_run_command(
            workspace_dir=workspace_dir,
            container_name=container_name,
            memory_limit_mb=max(memory_limit_mb, 128),
        ) + [
            self.image,
            f"/workspace/{binary_path.name}",
        ]

        started_at = time.monotonic()

        try:
            completed = self._run_command(
                command=command,
                timeout_sec=time_limit_ms / 1000,
                input_data=input_data,
                container_name=container_name,
            )
        except subprocess.TimeoutExpired as error:
            execution_time_ms = max(int((time.monotonic() - started_at) * 1000), time_limit_ms)
            return CppExecutionResult(
                status=CppExecutionStatus.TIME_LIMIT_EXCEEDED,
                execution_time_ms=execution_time_ms,
                stdout=_timeout_stream_to_text(error.stdout),
                stderr=_timeout_stream_to_text(error.stderr),
            )

        execution_time_ms = int((time.monotonic() - started_at) * 1000)

        if completed.returncode == 125:
            raise RuntimeError(completed.stderr.strip() or "Docker execution failed.")

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

    def _build_docker_run_command(
        self,
        *,
        workspace_dir: Path,
        container_name: str,
        memory_limit_mb: int,
    ) -> list[str]:
        workspace_mount = f"{workspace_dir.resolve()}:/workspace:rw"

        command = [
            self.docker_binary,
            "run",
            "--rm",
            "--name",
            container_name,
            "-i",
            "--network",
            "none",
            "--cpus",
            "1.0",
            "--memory",
            f"{memory_limit_mb}m",
            "--pids-limit",
            "128",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "-v",
            workspace_mount,
            "-w",
            "/workspace",
        ]

        command.extend(self._build_user_flags())
        return command

    def _build_user_flags(self) -> list[str]:
        if os.name == "nt":
            return []

        getuid = getattr(os, "getuid", None)
        getgid = getattr(os, "getgid", None)

        if getuid is None or getgid is None:
            return []

        return ["--user", f"{getuid()}:{getgid()}"]

    def _run_command(
        self,
        *,
        command: list[str],
        timeout_sec: float,
        input_data: str | None,
        container_name: str,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                f"Docker binary {self.docker_binary!r} is not available."
            ) from error
        except subprocess.TimeoutExpired:
            self._force_remove_container(container_name)
            raise
        except OSError as error:
            raise RuntimeError(f"Docker execution failed: {error}") from error

    def _force_remove_container(self, container_name: str) -> None:
        try:
            subprocess.run(
                [self.docker_binary, "rm", "-f", container_name],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return

    @staticmethod
    def _make_container_name(prefix: str) -> str:
        return f"contester-{prefix}-{uuid.uuid4().hex[:12]}"