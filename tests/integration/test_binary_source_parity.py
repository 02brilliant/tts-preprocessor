from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from engine.main import transform_with_rollout


pytestmark = pytest.mark.binary_runtime

ROOT_DIR = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT_DIR / "scripts" / "build_binary.sh"
RUNTIME_BINARY = ROOT_DIR / "dist" / "tts_preprocessor"

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
    return transform_with_rollout(text, mode="span_default")


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
