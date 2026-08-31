"""Executable checklist for policy §0.0.12 and §22 test-design themes.

This meta suite does not re-assert every behavioral example. It keeps the
required theme modules / §0.0.12 code-like email literal from disappearing
silently when suites are renamed or deleted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.main import transform


ROOT = Path(__file__).resolve().parents[2]

# policy.md §22 theme -> at least one existing suite path (repo-relative).
SECTION_22_THEME_MODULES: dict[str, tuple[str, ...]] = {
    "22.1 Canonical Examples": (
        "tests/policy/test_canonical_outputs_policy.py",
    ),
    "22.3 Forbidden Signature": (
        "tests/policy/test_forbidden_output_signatures_policy.py",
    ),
    "22.4 Shadow Validation": (
        "tests/span_engine/test_phase4_shadow_validation.py",
        "tests/span_engine/test_phase4_shadow_buffer.py",
    ),
    "22.5 Claim Registry": (
        "tests/policy/test_typed_surface_registry.py",
    ),
    "22.6 Gate": (
        "tests/policy/test_gate_policy.py",
    ),
    "22.7 Full Consume": (
        "tests/span_engine/test_large_unit_counter_full_claim.py",
    ),
    "22.8 Prosody Insert-only": (
        "tests/policy/test_prosody_insert_only_policy.py",
    ),
    "22.9 Bracket Policy": (
        "tests/span_engine/test_phase10_bracket_protection.py",
        "tests/span_engine/test_corner_and_curly_bracket_policy.py",
    ),
    "22.10 Jamo Reading": (
        "tests/span_engine/test_phase16b_jamo_basic.py",
    ),
    "22.11 Safe Particle Exception": (
        "tests/span_engine/test_phase10_unit_currency_safe_particle.py",
        "tests/span_engine/test_phase11_counter_safe_particle.py",
    ),
    "22.12 Dictionary": (
        "tests/span_engine/test_managed_lexicon_drift.py",
        "tests/policy/test_special_dictionary_josa.py",
    ),
    "22.13 Slash Compound Unit": (
        "tests/span_engine/test_decimal_compound_slash_units.py",
        "tests/span_engine/test_phase17a_compound_slash_unit_basic.py",
    ),
    "22.14 Code Separator": (
        "tests/span_engine/test_phase13_date_preserve.py",
        "tests/span_engine/test_phase15_hyphen_preserve.py",
    ),
    "22.15 Hangul Middle-dot Preservation": (
        "tests/policy/test_middle_dot_number_mode_policy.py",
    ),
    "22.16 Unsafe Tail Preserve": (
        "tests/span_engine/test_units_currency_compound_regression.py",
        "tests/span_engine/test_phase15_provenance_validation.py",
    ),
    "22.17 Area / Volume Unit": (
        "tests/span_engine/test_phase33c_superscript_unit_crash_guard.py",
        "tests/policy/test_counter_currency_units.py",
    ),
    "22.18 Mixed Large Unit Counter": (
        "tests/span_engine/test_large_unit_counter_full_claim.py",
        "tests/span_engine/test_batch6_large_number_ordinal_counter_boundaries.py",
    ),
    "22.19 Version / Log / Model Date-like Preserve": (
        "tests/span_engine/test_phase13_date_preserve.py",
        "tests/span_engine/test_phase15_hyphen_preserve.py",
        "tests/span_engine/test_managed_numeric_code_suffix.py",
    ),
    "22.20 Policy Consistency Regression": (
        "tests/policy/test_policy_reinforcement_extended_matrix.py",
        "tests/span_engine/test_phase37_v102_policy_corrections.py",
    ),
}

SECTION_00012_SUPPORTING_MODULES: tuple[str, ...] = (
    "tests/span_engine/test_phase35a_v101_policy_document_contract.py",
    "tests/span_engine/test_phase35a_korean_eligibility_gate.py",
    "tests/span_engine/test_phase35a_symbol_alias_expansion.py",
)


@pytest.mark.parametrize(
    ("theme", "paths"),
    list(SECTION_22_THEME_MODULES.items()),
    ids=list(SECTION_22_THEME_MODULES),
)
def test_section_22_theme_modules_exist(theme: str, paths: tuple[str, ...]) -> None:
    missing = [path for path in paths if not (ROOT / path).is_file()]
    assert not missing, f"{theme} missing suites: {missing}"


@pytest.mark.parametrize("path", SECTION_00012_SUPPORTING_MODULES)
def test_section_00012_supporting_modules_exist(path: str) -> None:
    assert (ROOT / path).is_file()


def test_section_00012_code_like_email_literal_is_preserved() -> None:
    # policy.md §0.0.12 Code-like exact preservation examples include this address.
    assert transform("test@example.com") == "test@example.com"


def test_llm_tests_are_on_default_pytest_testpaths() -> None:
    pytest_ini = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "testpaths" in pytest_ini
    assert "LLM/tests" in pytest_ini
    assert "tests" in pytest_ini
