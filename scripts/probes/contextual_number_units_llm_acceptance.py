from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.main import transform
from LLM.client import generate
from LLM.config import load_runtime_settings
from LLM.prompt_template import build_prompt
from LLM.response_validation import LLMStageContractError, validate_response


DEFAULT_FIXTURE = (
    ROOT_DIR
    / "tests"
    / "fixtures"
    / "contextual_number_unit_llm_acceptance.json"
)


@dataclass(frozen=True)
class AcceptanceCase:
    index: int
    group: str
    source: str
    expected: str


@dataclass(frozen=True)
class AcceptanceResult:
    index: int
    group: str
    source: str
    rule_text: str
    expected: str
    speech_text: str | None
    rule_exact: bool
    llm_accepted: bool | None
    error: str | None


def _load_cases(path: Path, selected_groups: set[str]) -> list[AcceptanceCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases: list[AcceptanceCase] = []
    for group_payload in payload:
        group = group_payload["group"]
        if selected_groups and group not in selected_groups:
            continue
        for source, expected in group_payload["cases"]:
            cases.append(
                AcceptanceCase(
                    index=len(cases) + 1,
                    group=group,
                    source=source,
                    expected=expected,
                )
            )
    return cases


def _allows_only_inserted_commas_and_spaces(
    expected: str,
    actual: str,
) -> bool:
    expected_index = 0
    for character in actual:
        if (
            expected_index < len(expected)
            and character == expected[expected_index]
        ):
            expected_index += 1
        elif character not in {",", " "}:
            return False
    return expected_index == len(expected)


def _run_case(case: AcceptanceCase, model: str | None) -> AcceptanceResult:
    rule_text = transform(case.source)
    if model is None:
        return AcceptanceResult(
            index=case.index,
            group=case.group,
            source=case.source,
            rule_text=rule_text,
            expected=case.expected,
            speech_text=None,
            rule_exact=rule_text == case.expected,
            llm_accepted=None,
            error=None,
        )

    try:
        generated = generate(
            model=model,
            prompt=build_prompt(rule_text),
            settings=load_runtime_settings(),
        )
        speech_text = validate_response(rule_text, generated.text)
    except Exception as exc:  # diagnostic runner reports provider/contract failures
        rejected_text = (
            exc.output_text if isinstance(exc, LLMStageContractError) else None
        )
        return AcceptanceResult(
            index=case.index,
            group=case.group,
            source=case.source,
            rule_text=rule_text,
            expected=case.expected,
            speech_text=rejected_text,
            rule_exact=rule_text == case.expected,
            llm_accepted=False,
            error=f"{type(exc).__name__}: {exc}",
        )

    return AcceptanceResult(
        index=case.index,
        group=case.group,
        source=case.source,
        rule_text=rule_text,
        expected=case.expected,
        speech_text=speech_text,
        rule_exact=rule_text == case.expected,
        llm_accepted=_allows_only_inserted_commas_and_spaces(
            case.expected,
            speech_text,
        ),
        error=None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare rule and optional local-LLM output against the contextual "
            "number-unit acceptance corpus."
        )
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--group", action="append", default=[])
    parser.add_argument("--model")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")

    cases = _load_cases(args.fixture, set(args.group))
    if args.workers == 1:
        results = [_run_case(case, args.model) for case in cases]
    else:
        completed: dict[int, AcceptanceResult] = {}
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(_run_case, case, args.model): case.index
                for case in cases
            }
            for future in as_completed(futures):
                result = future.result()
                completed[result.index] = result
        results = [completed[case.index] for case in cases]

    for result in results:
        if args.json:
            print(json.dumps(asdict(result), ensure_ascii=False))
            continue
        llm_status = (
            "-"
            if result.llm_accepted is None
            else "PASS"
            if result.llm_accepted
            else "FAIL"
        )
        print(
            f"{result.index:02d}\t{result.group}\t"
            f"rule={'PASS' if result.rule_exact else 'DIFF'}\t"
            f"llm={llm_status}\t{result.speech_text or result.error or result.rule_text}"
        )

    rule_passes = sum(result.rule_exact for result in results)
    print(f"RULE_SUMMARY {rule_passes}/{len(results)}")
    if args.model is None:
        return 0

    llm_passes = sum(result.llm_accepted is True for result in results)
    print(f"LLM_SUMMARY {llm_passes}/{len(results)}")
    return 0 if llm_passes == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
