from __future__ import annotations

import subprocess

from contester.judging.cpp_runner import CppCompilationStatus
from contester.judging.docker_runner import DockerRunner
from contester.judging.python_runner import PythonExecutionStatus


def test_execute_python_builds_expected_docker_command(tmp_path, monkeypatch) -> None:
    captured_commands: list[list[str]] = []
    captured_inputs: list[str | None] = []

    def fake_run(command, **kwargs):
        captured_commands.append(command)
        captured_inputs.append(kwargs.get("input"))
        return subprocess.CompletedProcess(command, 0, stdout="3\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = DockerRunner(image="contester-judge:local", docker_binary="docker")

    result = runner.execute_python(
        source_code="print(input())\n",
        input_data="3\n",
        time_limit_ms=1000,
        workspace_dir=tmp_path,
        memory_limit_mb=128,
    )

    assert result.status == PythonExecutionStatus.SUCCESS
    assert (tmp_path / "solution.py").read_text(encoding="utf-8") == "print(input())\n"

    command = captured_commands[0]
    assert command[:2] == ["docker", "run"]
    assert "-i" in command
    assert "--network" in command
    assert "none" in command
    assert "-v" in command
    assert "contester-judge:local" in command
    assert "python3" in command
    assert "/workspace/solution.py" in command
    assert captured_inputs[0] == "3\n"


def test_execute_python_timeout_forces_container_cleanup(tmp_path, monkeypatch) -> None:
    captured_commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        captured_commands.append(command)

        if len(command) >= 2 and command[1] == "run":
            raise subprocess.TimeoutExpired(
                cmd=command,
                timeout=kwargs["timeout"],
                output="partial-output",
                stderr="timeout",
            )

        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = DockerRunner(image="contester-judge:local", docker_binary="docker")

    result = runner.execute_python(
        source_code="while True:\n    pass\n",
        input_data="",
        time_limit_ms=100,
        workspace_dir=tmp_path,
        memory_limit_mb=128,
    )

    assert result.status == PythonExecutionStatus.TIME_LIMIT_EXCEEDED
    assert any(
        len(command) >= 4 and command[:3] == ["docker", "rm", "-f"]
        for command in captured_commands
    )


def test_compile_cpp_returns_compilation_error_on_nonzero_exit(tmp_path, monkeypatch) -> None:
    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="error: expected ';' before 'return'",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = DockerRunner(image="contester-judge:local", docker_binary="docker")

    result = runner.compile_cpp(
        source_code="#include <iostream>\nint main(){ std::cout << 1 return 0; }\n",
        workspace_dir=tmp_path,
        compiler="g++",
        timeout_sec=15,
        memory_limit_mb=128,
    )

    assert result.status == CppCompilationStatus.COMPILATION_ERROR
    assert result.binary_path is None
    assert "expected ';'" in result.stderr