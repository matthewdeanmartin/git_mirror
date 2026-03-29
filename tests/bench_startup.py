import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

import pytest


DEFAULT_MAX_STARTUP_SECONDS = 1.25
SAMPLES = 5
WARMUP_RUNS = 1


def _bench_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")
    env["XDG_CACHE_HOME"] = str(tmp_path / "xdg-cache")
    env["HISTFILE"] = str(tmp_path / "bash_history")
    env["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"
    env["PYTEST_CURRENT_TEST"] = "bench_startup"
    Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
    Path(env["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
    return env


def _measure_command(command: list[str], env: dict[str, str]) -> float:
    start = time.perf_counter()
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    return elapsed


@pytest.mark.slow
def test_cli_startup_benchmark(tmp_path):
    workspace_temp = tmp_path / "startup-bench"
    workspace_temp.mkdir(parents=True, exist_ok=True)
    env = _bench_env(workspace_temp)
    command = [sys.executable, "-m", "git_mirror", "--help"]

    for _ in range(WARMUP_RUNS):
        _measure_command(command, env)

    samples = [_measure_command(command, env) for _ in range(SAMPLES)]
    median_startup = statistics.median(samples)
    max_startup = float(os.environ.get("GIT_MIRROR_STARTUP_MAX_SECONDS", DEFAULT_MAX_STARTUP_SECONDS))

    print(f"startup samples={samples}")
    print(f"startup median={median_startup:.3f}s threshold={max_startup:.3f}s")

    assert median_startup <= max_startup
