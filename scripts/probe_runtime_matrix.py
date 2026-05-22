from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@dataclass(frozen=True, slots=True)
class ProbeCase:
    name: str
    text: str
    expected: str


@dataclass(frozen=True, slots=True)
class ProbeResult:
    runner: str
    case_name: str
    ok: bool
    expected: str
    actual: str
    error: str | None = None
    text: str = ""


RunnerFunc = Callable[[str], str]


def run_source_transform(text: str) -> str:
    from engine.span_engine.transform import transform

    return transform(text)


def run_production_source_transform(text: str) -> str:
    from engine.main import transform_with_rollout

    return transform_with_rollout(
        text,
        mode="span_default",
        include_debug=False,
    )


def run_binary_transform(binary_path: str | Path, text: str, timeout: int = 20) -> str:
    resolved_path = Path(binary_path).expanduser()
    if not resolved_path.exists():
        raise FileNotFoundError(f"binary does not exist: {resolved_path}")
    if not resolved_path.is_file():
        raise FileNotFoundError(f"binary path is not a file: {resolved_path}")

    try:
        result = subprocess.run(
            [
                str(resolved_path),
                "--rollout-mode",
                "span_default",
                f"--text={text}",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"binary execution timed out for input: {text!r}") from exc

    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "binary failed"
        raise RuntimeError(f"binary execution failed: {error}")

    output = result.stdout.rstrip("\n")
    if not output:
        raise RuntimeError("binary returned empty output")
    return output


def run_api_transform(base_url: str, text: str, timeout: int = 10) -> str:
    endpoint = base_url.rstrip("/") + "/api/transform"
    payload = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_payload = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    try:
        parsed = json.loads(response_payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"API returned invalid JSON: {response_payload!r}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"API returned non-object JSON: {parsed!r}")
    normalized = parsed.get("normalized_text")
    if not isinstance(normalized, str):
        raise RuntimeError(f"API response missing normalized_text: {parsed!r}")
    return normalized


def check_cases(
    runner_name: str,
    runner_func: RunnerFunc,
    cases: Iterable[ProbeCase],
    *,
    fail_fast: bool = True,
) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    for case in cases:
        result = _check_case(runner_name, runner_func, case)
        results.append(result)
        if fail_fast and not result.ok:
            break
    return results


def format_failure(result: ProbeResult) -> str:
    lines = [
        f"[FAIL] runner={result.runner}",
        f"case={result.case_name}",
        f"input={result.text!r}",
        f"expected={result.expected!r}",
    ]
    if result.error is not None:
        lines.append(f"error={result.error}")
    else:
        lines.append(f"actual={result.actual!r}")
    return "\n".join(lines)


def _check_case(
    runner_name: str,
    runner_func: RunnerFunc,
    case: ProbeCase,
) -> ProbeResult:
    try:
        actual = runner_func(case.text)
    except Exception as exc:
        return ProbeResult(
            runner=runner_name,
            case_name=case.name,
            ok=False,
            expected=case.expected,
            actual="",
            error=f"{type(exc).__name__}: {exc}",
            text=case.text,
        )

    return ProbeResult(
        runner=runner_name,
        case_name=case.name,
        ok=actual == case.expected,
        expected=case.expected,
        actual=actual,
        text=case.text,
    )
