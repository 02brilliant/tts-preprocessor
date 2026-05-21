from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
PYTHON_BIN = ROOT_DIR / ".venv" / "bin" / "python"
BUILD_BINARY_SCRIPT = ROOT_DIR / "scripts" / "build_binary.sh"
BINARY_PATH = ROOT_DIR / "dist" / "tts_preprocessor"
LARGE_UNIT_SMOKE_CASES = (
    (
        "2천8백28억, 2천8백28억테스트",
        "이천팔백이십팔억, 이천팔백이십팔억 테스트",
    ),
    (
        "2345억, 2,345억, 1만, 140만, 3백4십만, 5억4천만, 12만3천4백, 2백만3천4백, 54천만, 1억2천3백만4천5백, 25.50억, 2천8백28억테스트, 2천8백28억abc",
        "이천삼백사십오억, 이천삼백사십오억, 일만, 백사십만, 삼백사십만, 오억사천만, 십이만삼천사백, 이백만삼천사백, 오십사천만, 일억이천삼백만사천오백, 이십오쩜오영 억, 이천팔백이십팔억 테스트, 이천팔백이십팔억abc",
    ),
)


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


def run_large_unit_binary_smoke() -> subprocess.CompletedProcess[str]:
    # Release must verify the packaged binary path, which is the API runtime contract.
    if not BINARY_PATH.exists():
        return subprocess.CompletedProcess(
            args=[str(BINARY_PATH)],
            returncode=1,
            stdout="",
            stderr=f"Binary not found: {BINARY_PATH}",
        )

    for text, expected in LARGE_UNIT_SMOKE_CASES:
        result = subprocess.run(
            [str(BINARY_PATH), "--rollout-mode", "span_default", "--text", text],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
        )
        actual = result.stdout.rstrip("\n")
        if result.returncode != 0:
            return result
        if actual != expected:
            return subprocess.CompletedProcess(
                args=result.args,
                returncode=1,
                stdout=result.stdout,
                stderr=(
                    "Large-unit binary smoke failed\n"
                    f"input={text!r}\n"
                    f"expected={expected!r}\n"
                    f"actual={actual!r}\n"
                ),
            )

    return subprocess.CompletedProcess(
        args=[str(BINARY_PATH), "--rollout-mode", "span_default"],
        returncode=0,
        stdout="Large-unit binary smoke passed.\n",
        stderr="",
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

    binary_smoke_result = run_large_unit_binary_smoke()
    if binary_smoke_result.stdout:
        print(
            binary_smoke_result.stdout,
            end="" if binary_smoke_result.stdout.endswith("\n") else "\n",
        )
    if binary_smoke_result.stderr:
        print(
            binary_smoke_result.stderr,
            file=sys.stderr,
            end="" if binary_smoke_result.stderr.endswith("\n") else "\n",
        )

    if binary_smoke_result.returncode != 0:
        print("Binary large-unit smoke failed. Release aborted.", file=sys.stderr)
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

    print("Release completed: downloads/tts-preprocessor.zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
