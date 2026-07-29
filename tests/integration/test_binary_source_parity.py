from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import api.server as api_server
from engine.main import transform
from tests._production_boundary import (
    REQUIRED_BINARY_MODULES,
    unexpected_binary_modules,
)


pytestmark = pytest.mark.binary_runtime

ROOT_DIR = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT_DIR / "scripts" / "build_binary.sh"
RUNTIME_BINARY = ROOT_DIR / "dist" / "tts_preprocessor"
GOLDEN_CORPUS_PATH = ROOT_DIR / "tests" / "fixtures" / "production_golden.jsonl"

BATCH1_FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "batch1_allowed_output_diffs.json"
BATCH2_FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "batch2_allowed_output_diffs.json"

BATCH3_FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "batch3_allowed_output_diffs.json"
BATCH4_FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "batch4_allowed_output_diffs.json"
BATCH5_FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "batch5_allowed_output_diffs.json"
BATCH6_FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "batch6_allowed_output_diffs.json"
BATCH7_FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "batch7_allowed_output_diffs.json"
BATCH8_FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "batch8_allowed_output_diffs.json"


def _load_golden_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in GOLDEN_CORPUS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


GOLDEN_CASES = _load_golden_cases()


def _load_batch1_cases() -> list[dict[str, str]]:
    fixture = json.loads(BATCH1_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert all(row["status"] == "applied" for row in fixture["allowed_diffs"])
    stable_cases = [
        {
            "decision_id": row["decision_id"],
            "input": row["input"],
            "expected": row["expected"],
        }
        for row in fixture["stable_decisions"]
    ]
    diff_cases = [
        {"decision_id": row["decision_id"], "input": row["input"], "expected": row["after"]}
        for row in fixture["allowed_diffs"]
    ]
    return stable_cases + diff_cases


BATCH1_CASES = _load_batch1_cases()


def _load_batch2_cases() -> list[dict[str, str]]:
    fixture = json.loads(BATCH2_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["allowed_diffs"] == []
    return [
        {
            "decision_id": row["decision_id"],
            "input": row["input"],
            "expected": row["expected"],
        }
        for row in fixture["stable_decisions"]
    ]


BATCH2_CASES = _load_batch2_cases()


def _load_batch3_cases() -> list[dict[str, str]]:
    fixture = json.loads(BATCH3_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["allowed_diffs"] == []
    return [
        {
            "decision_id": row["decision_id"],
            "input": row["input"],
            "expected": row["expected"],
        }
        for row in fixture["stable_decisions"]
    ]


BATCH3_CASES = _load_batch3_cases()


def _load_batch4_cases() -> list[dict[str, str]]:
    fixture = json.loads(BATCH4_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert all(row["status"] == "applied" for row in fixture["allowed_diffs"])
    stable_cases = [
        {
            "decision_id": row["decision_id"],
            "input": row["input"],
            "expected": row["expected"],
        }
        for row in fixture["stable_decisions"]
    ]
    diff_cases = [
        {"decision_id": row["decision_id"], "input": row["input"], "expected": row["after"]}
        for row in fixture["allowed_diffs"]
    ]
    return stable_cases + diff_cases


BATCH4_CASES = _load_batch4_cases()


def _load_batch5_cases() -> list[dict[str, str]]:
    fixture = json.loads(BATCH5_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["allowed_diffs"] == []
    return [
        {
            "decision_id": row["decision_id"],
            "input": row["input"],
            "expected": row["expected"],
        }
        for row in fixture["stable_decisions"]
    ]


BATCH5_CASES = _load_batch5_cases()


def _load_stable_batch_cases(path: Path) -> list[dict[str, str]]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    assert fixture["allowed_diffs"] == []
    return [
        {
            "decision_id": row["decision_id"],
            "input": row["input"],
            "expected": row["expected"],
        }
        for row in fixture["stable_decisions"]
    ]


BATCH6_CASES = _load_stable_batch_cases(BATCH6_FIXTURE_PATH)
BATCH7_CASES = _load_stable_batch_cases(BATCH7_FIXTURE_PATH)
BATCH8_CASES = _load_stable_batch_cases(BATCH8_FIXTURE_PATH)


PARITY_CASES = [
    pytest.param("AI는 2025-01-03에 3kg 제품을 69% 할인한다", id="short-acronym-date-unit"),
    pytest.param("FTA는 유지하고 AI는 투자한다", id="acronym"),
    pytest.param("AI·반도체 전략은 6402억 달러 규모다", id="mixed-token-large-unit"),
    pytest.param("3~8cm는 유지된다", id="range"),
    pytest.param("제62회는 1대1로 끝났다", id="event-number"),
    pytest.param("6402억 달러 규모다", id="large-unit"),
    pytest.param("2천8백28억, 2천8백28억테스트", id="large-unit-mixed-smoke"),
    pytest.param(
        "2345억, 2,345억, 1만, 140만, 3백4십만, 5억4천만, 12만3천4백, "
        "2백만3천4백, 54천만, 1억2천3백만4천5백, 25.50억, "
        "2천8백28억테스트, 2천8백28억abc",
        id="large-unit-integrated-smoke",
    ),
    pytest.param("안녕하세요, FTA는 유지한다.", id="punctuation-preservation"),
    pytest.param("전문가 유로을 AI가 FTA은", id="core-invariance"),
]

LONG_NEWS_SAMPLE = (
    "정부는 AI·반도체 전략을 발표하며 2025-01-03부터 3~8cm 공정 장비와 "
    "6402억 달러 규모의 투자 계획을 단계적으로 집행한다고 밝혔다. "
    "제62회 회의에서는 FTA는 유지하고 AI는 확대한다는 방침과 함께 "
    "13:05 브리핑 이후 세부 정책 문안을 공개했다."
)


def _latest_source_mtime() -> float:
    paths = [
        ROOT_DIR / "bin" / "build_binary_entrypoint.py",
        ROOT_DIR / "scripts" / "build_binary.sh",
        ROOT_DIR / "tts_preprocessor.spec",
    ]
    paths.extend(path for path in (ROOT_DIR / "engine").rglob("*.py"))
    paths.extend(path for path in (ROOT_DIR / "engine" / "data").rglob("*") if path.is_file())
    return max(path.stat().st_mtime for path in paths)


@pytest.fixture(scope="session")
def runtime_binary_path() -> Path:
    needs_build = not RUNTIME_BINARY.exists() or RUNTIME_BINARY.stat().st_mtime < _latest_source_mtime()
    if needs_build:
        subprocess.run(
            ["bash", str(BUILD_SCRIPT)],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )

    if not RUNTIME_BINARY.exists():
        raise AssertionError(f"Runtime binary missing: {RUNTIME_BINARY}")
    return RUNTIME_BINARY


def _run_binary(binary_path: Path, text: str) -> str:
    result = subprocess.run(
        [str(binary_path)],
        input=text,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr.strip() or result.stdout.strip()
    return result.stdout.rstrip("\n")


def official_production_source_transform(text: str) -> str:
    """Binary output must match the official source-side production entrypoint."""
    return transform(text)


@pytest.mark.parametrize("text", PARITY_CASES)
def test_binary_matches_source_for_representative_inputs(runtime_binary_path: Path, text: str):
    assert _run_binary(runtime_binary_path, text) == official_production_source_transform(text)


def test_binary_matches_source_for_long_news_sample(runtime_binary_path: Path):
    assert _run_binary(runtime_binary_path, LONG_NEWS_SAMPLE) == official_production_source_transform(LONG_NEWS_SAMPLE)


def test_binary_stdout_contract_is_stable(runtime_binary_path: Path):
    text = "FTA는 유지한다"
    result = subprocess.run(
        [str(runtime_binary_path), "--text", text],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr.strip() or result.stdout.strip()
    assert result.stdout.rstrip("\n") == official_production_source_transform(text)


@pytest.mark.parametrize(
    "case", BATCH1_CASES, ids=lambda case: "batch1-" + case["decision_id"]
)
def test_binary_matches_batch1_output_contract(
    runtime_binary_path: Path, case: dict[str, str]
) -> None:
    assert _run_binary(runtime_binary_path, case["input"]) == case["expected"]


@pytest.mark.parametrize(
    "case", BATCH2_CASES, ids=lambda case: "batch2-" + case["decision_id"]
)
def test_binary_matches_batch2_output_contract(
    runtime_binary_path: Path, case: dict[str, str]
) -> None:
    assert _run_binary(runtime_binary_path, case["input"]) == case["expected"]


@pytest.mark.parametrize(
    "case", BATCH3_CASES, ids=lambda case: "batch3-" + case["decision_id"]
)
def test_binary_matches_batch3_output_contract(
    runtime_binary_path: Path, case: dict[str, str]
) -> None:
    assert _run_binary(runtime_binary_path, case["input"]) == case["expected"]


@pytest.mark.parametrize(
    "case", BATCH4_CASES, ids=lambda case: "batch4-" + case["decision_id"]
)
def test_binary_matches_batch4_output_contract(
    runtime_binary_path: Path, case: dict[str, str]
) -> None:
    assert _run_binary(runtime_binary_path, case["input"]) == case["expected"]


@pytest.mark.parametrize(
    "case", BATCH5_CASES, ids=lambda case: "batch5-" + case["decision_id"]
)
def test_binary_matches_batch5_output_contract(
    runtime_binary_path: Path, case: dict[str, str]
) -> None:
    assert _run_binary(runtime_binary_path, case["input"]) == case["expected"]


@pytest.mark.parametrize(
    ("batch_id", "case"),
    [
        pytest.param(6, case, id="batch6-" + case["decision_id"])
        for case in BATCH6_CASES
    ]
    + [
        pytest.param(7, case, id="batch7-" + case["decision_id"])
        for case in BATCH7_CASES
    ]
    + [
        pytest.param(8, case, id="batch8-" + case["decision_id"])
        for case in BATCH8_CASES
    ],
)
def test_binary_matches_batch6_to_batch8_output_contract(
    runtime_binary_path: Path, batch_id: int, case: dict[str, str]
) -> None:
    assert batch_id in {6, 7, 8}
    assert _run_binary(runtime_binary_path, case["input"]) == case["expected"]


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda case: "golden-" + case["id"])
def test_binary_matches_fixed_production_snapshot(
    runtime_binary_path: Path,
    case: dict,
) -> None:
    assert _run_binary(runtime_binary_path, case["input"]) == case["expected"]


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda case: "golden-" + case["id"])
def test_api_matches_fixed_production_snapshot(
    runtime_binary_path: Path,
    case: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TTS_PREPROCESSOR_BINARY", str(runtime_binary_path))

    assert api_server.transform_request_payload({"text": case["input"]}) == {
        "normalized_text": case["expected"]
    }


def test_binary_archive_contains_only_production_engine_modules(
    runtime_binary_path: Path,
) -> None:
    archive_viewer = Path(sys.executable).with_name("pyi-archive_viewer")
    assert archive_viewer.exists(), archive_viewer

    result = subprocess.run(
        [str(archive_viewer), "-r", "-b", str(runtime_binary_path)],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    engine_modules = {
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip().startswith("engine.")
    }

    assert unexpected_binary_modules(engine_modules) == []
    missing_required = sorted(set(REQUIRED_BINARY_MODULES) - engine_modules)
    assert missing_required == []
