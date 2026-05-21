from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
PYTHON_BIN = ROOT_DIR / ".venv" / "bin" / "python"
BUILD_BINARY_SCRIPT = ROOT_DIR / "scripts" / "build_binary.sh"
PACKAGE_BINARY_PATH = ROOT_DIR / "packages" / "tts-preprocessor" / "bin" / "tts_preprocessor"
SEMANTIC_PROBE_RUNNER = ROOT_DIR / "scripts" / "probes" / "run_semantic_probes.py"


def run_pytest(*extra_args: str) -> subprocess.CompletedProcess[str]:
    python_bin = str(PYTHON_BIN if PYTHON_BIN.exists() else sys.executable)
    return subprocess.run(
        [python_bin, "-m", "pytest", "-q", "--capture=no", *extra_args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )


def run_build_binary() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(BUILD_BINARY_SCRIPT)],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )


def run_semantic_binary_probes(binary_path: Path, label: str) -> subprocess.CompletedProcess[str]:
    if not binary_path.exists():
        return subprocess.CompletedProcess(
            args=[str(binary_path)],
            returncode=1,
            stdout="",
            stderr=f"{label} binary not found: {binary_path}",
        )
    if not SEMANTIC_PROBE_RUNNER.exists():
        return subprocess.CompletedProcess(
            args=[str(SEMANTIC_PROBE_RUNNER)],
            returncode=1,
            stdout="",
            stderr=f"Semantic probe runner not found: {SEMANTIC_PROBE_RUNNER}",
        )

    python_bin = str(PYTHON_BIN if PYTHON_BIN.exists() else sys.executable)
    return subprocess.run(
        [
            python_bin,
            str(SEMANTIC_PROBE_RUNNER),
            "--runtime",
            "binary",
            "--binary",
            str(binary_path),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )


def run_build() -> subprocess.CompletedProcess[str]:
    python_bin = str(PYTHON_BIN if PYTHON_BIN.exists() else sys.executable)
    return subprocess.run(
        [python_bin, "scripts/build_package.py"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("Usage: python scripts/release.py [ignored-version]", file=sys.stderr)
        return 1

    test_result = run_pytest("-m", "not binary_runtime")
    if test_result.stdout:
        print(test_result.stdout, end="" if test_result.stdout.endswith("\n") else "\n")
    if test_result.stderr:
        print(test_result.stderr, file=sys.stderr, end="" if test_result.stderr.endswith("\n") else "\n")

    if test_result.returncode != 0:
        print("Source tests failed. Release aborted.", file=sys.stderr)
        return 1

    print("Source tests passed.")

    binary_build_result = run_build_binary()
    if binary_build_result.stdout:
        print(
            binary_build_result.stdout,
            end="" if binary_build_result.stdout.endswith("\n") else "\n",
        )
    if binary_build_result.stderr:
        print(
            binary_build_result.stderr,
            file=sys.stderr,
            end="" if binary_build_result.stderr.endswith("\n") else "\n",
        )

    if binary_build_result.returncode != 0:
        print("Binary build failed. Release aborted.", file=sys.stderr)
        return 1

    binary_test_result = run_pytest("-m", "binary_runtime")
    if binary_test_result.stdout:
        print(
            binary_test_result.stdout,
            end="" if binary_test_result.stdout.endswith("\n") else "\n",
        )
    if binary_test_result.stderr:
        print(
            binary_test_result.stderr,
            file=sys.stderr,
            end="" if binary_test_result.stderr.endswith("\n") else "\n",
        )

    if binary_test_result.returncode != 0:
        print("Binary runtime tests failed. Release aborted.", file=sys.stderr)
        return 1

    print("Binary runtime tests passed.")

    build_result = run_build()
    if build_result.stdout:
        print(build_result.stdout, end="" if build_result.stdout.endswith("\n") else "\n")
    if build_result.stderr:
        print(build_result.stderr, file=sys.stderr, end="" if build_result.stderr.endswith("\n") else "\n")

    if build_result.returncode != 0:
        return build_result.returncode

    packaged_probe_result = run_semantic_binary_probes(PACKAGE_BINARY_PATH, "packaged binary")
    if packaged_probe_result.stdout:
        print(
            packaged_probe_result.stdout,
            end="" if packaged_probe_result.stdout.endswith("\n") else "\n",
        )
    if packaged_probe_result.stderr:
        print(
            packaged_probe_result.stderr,
            file=sys.stderr,
            end="" if packaged_probe_result.stderr.endswith("\n") else "\n",
        )

    if packaged_probe_result.returncode != 0:
        print("Packaged binary semantic probe failed. Release aborted.", file=sys.stderr)
        return 1

    print("Release completed: downloads/tts-preprocessor.zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
