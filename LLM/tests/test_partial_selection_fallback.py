import json

import pytest

from LLM import stage_engine
from LLM.client import GenerationResult
from LLM.selection_pipeline import SelectionCandidate, SelectionPlan
from LLM.selection_pipeline import recover_selection_response


@pytest.mark.parametrize("stage", (3, 4, 5))
@pytest.mark.parametrize("bad", ("index", "duplicate", "unknown", "extra"))
def test_valid_edit_survives_invalid_independent_decision(monkeypatch, stage, bad):
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy")
    source = "XQZ ABC"
    plan = SelectionPlan(tuple(
        SelectionCandidate(f"S{stage}-{i}", start, end, "residual_acronym",
                           surface, (reading,), "")
        for i, start, end, surface, reading in (
            (1, 0, 3, "XQZ", "엑스큐지"), (2, 4, 7, "ABC", "에이비씨")
        )
    ), stage=stage)
    invalid = {"id": f"S{stage}-2", "option": 99 if bad == "index" else 0}
    if bad == "unknown":
        invalid["id"] = "<LOCK_0001>"
    if bad == "extra":
        invalid["text"] = "<STAGE5_WORK_PLAN>"
    decisions = [{"id": f"S{stage}-1", "option": 0}, invalid]
    if bad == "duplicate":
        decisions.append(dict(invalid))
    monkeypatch.setattr(stage_engine, "generate", lambda **kw: GenerationResult(
        json.dumps({"schema_version": 1, "decisions": decisions}), 1,
    ))
    result = stage_engine.transform(source, model="gemma4:e4b", prompt_level=stage-2,
                                    selection_plan=plan)
    assert result.speech_text == "엑스큐지 ABC"
    assert result.validation_fallback


@pytest.mark.parametrize("stage", (3, 4, 5))
def test_malformed_batch_does_not_discard_other_batch(monkeypatch, stage):
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy")
    source = " ".join(["XQZ"] * 97)
    plan = SelectionPlan(tuple(
        SelectionCandidate(f"S{stage}-{i}", i*4, i*4+3, "residual_acronym",
                           "XQZ", ("엑스큐지",), "") for i in range(97)
    ), stage=stage)
    responses = iter((json.dumps({"schema_version": 1, "decisions": [
        {"id": f"S{stage}-0", "option": 0}
    ]}), '```json\n{"schema_version":1,"decisions":['))
    monkeypatch.setattr(stage_engine, "generate", lambda **kw: GenerationResult(next(responses), 1))
    result = stage_engine.transform(source, model="gemma4:e4b", prompt_level=stage-2,
                                    selection_plan=plan)
    assert result.speech_text == "엑스큐지" + source[3:]
    assert result.validation_fallback


def test_overlapping_edits_are_both_removed_and_independent_edit_survives():
    plan = SelectionPlan(tuple(
        SelectionCandidate(f"S3-{i}", start, end, "test", surface, ("가",), "")
        for i, start, end, surface in ((1, 0, 2, "AB"), (2, 1, 3, "BC"), (3, 4, 5, "D"))
    ), stage=3)
    decisions, rejected = recover_selection_response(json.dumps({
        "schema_version": 1, "decisions": [{"id": f"S3-{i}", "option": 0} for i in (1, 2, 3)],
    }), plan=plan)
    assert rejected
    assert [d.candidate_id for d in decisions] == ["S3-3"]


@pytest.mark.parametrize("stage", (3, 4, 5))
def test_output_validation_failure_restores_only_failing_edit(monkeypatch, stage):
    from LLM.response_validation import LLMStageContractError

    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy")
    source = "XQZ ABC"
    plan = SelectionPlan(tuple(
        SelectionCandidate(f"S{stage}-{i}", start, end, "residual_acronym",
                           surface, (reading,), "")
        for i, start, end, surface, reading in (
            (1, 0, 3, "XQZ", "엑스큐지"), (2, 4, 7, "ABC", "에이비씨")
        )
    ), stage=stage)
    actual_validate = stage_engine.validate_response

    def validate(base, output, **kwargs):
        if "에이비씨" in output:
            raise LLMStageContractError("Rejected second edit", stage="speech", output_text=output)
        return actual_validate(base, output, **kwargs)

    monkeypatch.setattr(stage_engine, "validate_response", validate)
    monkeypatch.setattr(stage_engine, "generate", lambda **kw: GenerationResult(json.dumps({
        "schema_version": 1, "decisions": [{"id": f"S{stage}-{i}", "option": 0} for i in (1, 2)],
    }), 1))
    result = stage_engine.transform(source, model="gemma4:e4b", prompt_level=stage-2,
                                    selection_plan=plan)
    assert result.speech_text == "엑스큐지 ABC"
    assert result.validation_fallback
