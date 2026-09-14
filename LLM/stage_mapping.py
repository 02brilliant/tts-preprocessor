from __future__ import annotations


PROMPT_LEVEL_TO_STAGE = {1: 3, 3: 4}
LLM_STAGES = frozenset({3, 4})
PUBLIC_LEVELS = frozenset({0, 1, 2, 3, 4})


def stage_for_prompt_level(prompt_level: int) -> int:
    try:
        return PROMPT_LEVEL_TO_STAGE[prompt_level]
    except KeyError as exc:
        raise ValueError("prompt_level must be 1 or 3") from exc


def prompt_level_for_stage(stage: int) -> int:
    for prompt_level, mapped in PROMPT_LEVEL_TO_STAGE.items():
        if mapped == stage:
            return prompt_level
    raise ValueError("stage must be 3 or 4")
