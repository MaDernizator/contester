from __future__ import annotations

import os
import stat
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
    def __init__(
        self,
        *,
        image: str,
        docker_binary: str = "docker",
        shared_volume_name: str,
        shared_mount_path: str,
    ) -> None:
        self.image = image
        self.docker_binary = docker_binary
        self.shared_volume_name = shared_volume_name
        self.shared_mount_path = Path(shared_mount_path)
        self._resolved_volume_mountpoint: Path | None = None

    def execute_python(
        self,
        *,
        source_code: str,
        input_data: str,
        time_limit_ms: int,
        workspace_dir: Path,
        memory_limit_mb: int,
    ) -> PythonExecutionResult:
        self._prepare_workspace(workspace_dir)

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
        self._prepare_workspace(workspace_dir)

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
        self._prepare_workspace(workspace_dir)

        container_name = self._make_container_name("cpp-run")
        command = self._build_docker_run_command(
            workspace_dir=workspace_dir,
            container_name=container_name,
            memory_limit_mb=max(memory_limit_mb, 128),
        ) + [
            self.image,
            "/workspace/solution",
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
        daemon_workspace_dir = self._resolve_daemon_workspace_dir(workspace_dir)

        return [
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
            "--memory-swap",
            f"{memory_limit_mb}m",
            "--pids-limit",
            "128",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--ulimit",
            "nofile=1024:1024",
            "-v",
            f"{daemon_workspace_dir}:/workspace:rw",
            "-w",
            "/workspace",
        ]

    def _prepare_workspace(self, workspace_dir: Path) -> None:
        workspace_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(workspace_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

    def _resolve_daemon_workspace_dir(self, workspace_dir: Path) -> Path:
        volume_mountpoint = self._get_shared_volume_mountpoint()

        try:
            relative_workspace_dir = workspace_dir.resolve().relative_to(
                self.shared_mount_path.resolve()
            )
        except ValueError as error:
            raise RuntimeError(
                f"Workspace path {workspace_dir!s} is outside shared mount path "
                f"{self.shared_mount_path!s}."
            ) from error

        daemon_workspace_dir = volume_mountpoint / relative_workspace_dir
        daemon_workspace_dir.mkdir(parents=True, exist_ok=True)
        return daemon_workspace_dir

    def _get_shared_volume_mountpoint(self) -> Path:
        if self._resolved_volume_mountpoint is not None:
            return self._resolved_volume_mountpoint

        command = [
            self.docker_binary,
            "volume",
            "inspect",
            "--format",
            "{{ .Mountpoint }}",
            self.shared_volume_name,
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                f"Docker binary {self.docker_binary!r} is not available."
            ) from error
        except OSError as error:
            raise RuntimeError(f"Failed to inspect Docker volume: {error}") from error

        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.strip()
                or f"Failed to inspect Docker volume {self.shared_volume_name!r}."
            )

        mountpoint = Path(completed.stdout.strip())
        if not mountpoint.is_absolute():
            raise RuntimeError(
                f"Invalid Docker volume mountpoint returned for {self.shared_volume_name!r}: "
                f"{mountpoint!s}"
            )

        self._resolved_volume_mountpoint = mountpoint
        return mountpoint

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
