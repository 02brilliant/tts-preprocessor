from __future__ import annotations

from engine.pipeline import transform_engine
from engine.pipeline.surfaces import HelperKind, SurfaceType
from engine.pipeline.transform_engine import HelperPhase, normalize_text
from engine.rules import base_rules


def test_rule_pipeline_stage_order_matches_unified_policy():
    assert [stage.name for stage in base_rules.RULE_PIPELINE] == [
        "date_range",
        "hyphen_digit_blocks",
        "date_time",
        "special_unit",
        "special",
        "emergency",
        "percent_currency",
        "compound_unit",
        "simple_unit",
        "fraction",
        "counter_noun",
        "duration",
        "unit",
        "spaced_middle_dot",
        "middle_dot_structured",
        "number",
        "final_range",
    ]
    assert all(stage.role == base_rules.RuleStageRole.STRUCTURED_PARSER for stage in base_rules.RULE_PIPELINE)


def test_restricted_helper_order_and_taxonomy_match_unified_policy():
    assert [helper.name for helper in transform_engine.RESTRICTED_HELPERS] == [
        "_adjust_number_noun_particles",
        "_fix_numeric_postpositions",
        "_fix_josa_number_spacing",
        "_fix_decimal_reading_spacing",
        "_fix_numeric_label_suffix_spacing",
        "_fix_residual_integer_degrees",
        "_fix_standalone_jo",
        "_fix_standalone_eok",
        "_fix_residual_english_units",
        "_fix_compact_date_counter_spacing",
    ]
    assert transform_engine.RESTRICTED_HELPERS[0].helper_kind == HelperKind.STRUCTURED_PARSER
    assert transform_engine.RESTRICTED_HELPERS[1].helper_kind == HelperKind.GENERIC_STRING
    assert transform_engine.PHONETIC_HELPER.phase == HelperPhase.RESTRICTED
    assert transform_engine.PHONETIC_HELPER.helper_kind == HelperKind.STRUCTURED_PARSER


def test_hyphen_digit_blocks_do_not_fall_through_emergency_or_counter_surface_paths():
    result = normalize_text("1-1-9")
    assert result.text == "일 일 구"
    assert any("hyphen_digit_block_routing:pass" in entry for entry in result.gate_logs)
    assert not any("emergency_context" in entry for entry in result.gate_logs)
    assert all(span.surface.surface_type != SurfaceType.COUNTER_SURFACE for span in result.rendered_surfaces)


def test_phone_owner_stays_on_special_phone_route():
    result = normalize_text("1234-5678")
    assert result.text == "일이삼사 오육칠팔"
    assert any("hyphen_phone_routing:pass" in entry for entry in result.gate_logs)
    assert not any("hyphen_digit_block_routing" in entry for entry in result.gate_logs)


def test_dotted_event_preserve_does_not_emit_event_surface_or_decimal_output():
    result = normalize_text("12.3 비상계엄")
    assert result.text == "12.3 비상계엄"
    assert not result.rendered_surfaces
    assert any("event_keyword:fail" in entry for entry in result.gate_logs)
    assert any("decimal_context:fail" in entry for entry in result.gate_logs)
