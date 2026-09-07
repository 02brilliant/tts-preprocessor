from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

from LLM.config import LLM_PROMPT_LV2_PATH, LLM_PROMPT_LV3_PATH, LLM_PROMPT_PATH
from LLM.selection_pipeline import SelectionPlan, build_selection_plan


INPUT_PLACEHOLDER = "{{NORMALIZED_TEXT}}"
STAGE3_WORK_PLAN_PLACEHOLDER = "{{STAGE3_WORK_PLAN}}"
STAGE4_WORK_PLAN_PLACEHOLDER = "{{STAGE4_WORK_PLAN}}"
STAGE5_WORK_PLAN_PLACEHOLDER = "{{STAGE5_WORK_PLAN}}"
PROMPT_FILE_LABEL = "LLM/docs/LLM_prompt.txt"
PROMPT_LV2_FILE_LABEL = "LLM/docs/LLM_prompt_lv2.txt"
PROMPT_LV3_FILE_LABEL = "LLM/docs/LLM_prompt_lv3.txt"
PROMPT_PATHS = {
    1: (LLM_PROMPT_PATH, PROMPT_FILE_LABEL),
    2: (LLM_PROMPT_LV2_PATH, PROMPT_LV2_FILE_LABEL),
    3: (LLM_PROMPT_LV3_PATH, PROMPT_LV3_FILE_LABEL),
}


class PromptTemplateError(ValueError):
    """Raised when the editable prompt template cannot be used safely."""


def build_prompt(
    normalized_text: str,
    path: Path | None = None,
    *,
    prompt_level: int = 1,
    selection_plan: SelectionPlan | None = None,
) -> str:
    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be a string")

    if isinstance(prompt_level, bool) or prompt_level not in PROMPT_PATHS:
        raise PromptTemplateError("LLM prompt_level must be 1, 2, or 3.")

    configured_path, configured_label = PROMPT_PATHS[prompt_level]
    selected_path = path if path is not None else configured_path
    file_label = PROMPT_FILE_LABEL if path is not None else configured_label

    try:
        template = (
            _read_packaged_template(selected_path)
            if path is None
            else selected_path.read_text(encoding="utf-8")
        )
    except FileNotFoundError as exc:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})을 찾을 수 없습니다. "
            "파일을 복원한 뒤 다시 실행하세요."
        ) from exc
    except UnicodeDecodeError as exc:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})은 UTF-8 인코딩이어야 합니다. "
            "파일을 UTF-8로 저장한 뒤 다시 실행하세요."
        ) from exc

    placeholder_count = template.count(INPUT_PLACEHOLDER)
    if placeholder_count == 0:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})에 "
            f"{INPUT_PLACEHOLDER} 자리표시자가 없습니다. "
            "원고를 넣을 위치에 이 자리표시자를 정확히 한 번 추가한 뒤 다시 실행하세요."
        )
    if placeholder_count > 1:
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})에 "
            f"{INPUT_PLACEHOLDER} 자리표시자가 {placeholder_count}개 있습니다. "
            "하나만 남긴 뒤 다시 실행하세요."
        )
    placeholders = (
        STAGE3_WORK_PLAN_PLACEHOLDER,
        STAGE4_WORK_PLAN_PLACEHOLDER,
        STAGE5_WORK_PLAN_PLACEHOLDER,
    )
    placeholder = placeholders[prompt_level - 1]
    if template.count(placeholder) != 1 or any(
        other in template for other in placeholders if other != placeholder
    ):
        raise PromptTemplateError(
            f"AI LLM 프롬프트 파일({file_label})에 "
            f"{placeholder} 자리표시자가 정확히 하나 필요합니다."
        )
    plan = selection_plan or build_selection_plan(
        normalized_text,
        stage=prompt_level + 2,
    )
    plan.validate_for_text(normalized_text, stage=prompt_level + 2)
    return _render_template(template, normalized_text, placeholder, plan)


def _render_template(
    template: str,
    text: str,
    placeholder: str,
    plan: SelectionPlan,
) -> str:
    values = {INPUT_PLACEHOLDER: text, placeholder: plan.to_prompt_json()}
    return re.sub(
        r"\{\{(?:NORMALIZED_TEXT|STAGE[345]_WORK_PLAN)\}\}",
        lambda match: values[match.group()],
        template,
    )


@lru_cache(maxsize=3)
def _read_packaged_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")
