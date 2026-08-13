from __future__ import annotations

import sys

from LLM.client import LLMClientError
from LLM.config import ConfigurationError, load_model_config, load_vllm_settings
from LLM.prompt_template import PromptTemplateError, build_prompt
from LLM.response_validation import validate_response
from LLM.vllm_client import VllmClientError, generate_vllm


SMOKE_NORMALIZED_TEXT = "에이아이는 삼 킬로그램 제품을 소개했다."


def main() -> int:
    try:
        settings = load_vllm_settings()
        model_config = load_model_config()
    except ConfigurationError as exc:
        print(f"[vllm-smoke][ERROR] {exc}", file=sys.stderr)
        return 1

    failed = False
    for definition in model_config.definitions:
        if definition.provider != "vllm":
            continue
        try:
            result = generate_vllm(
                model=definition.upstream_model,
                prompt=build_prompt(SMOKE_NORMALIZED_TEXT),
                settings=settings,
            )
            speech_text = validate_response(
                SMOKE_NORMALIZED_TEXT,
                result.text,
            )
        except (VllmClientError, LLMClientError, PromptTemplateError) as exc:
            failed = True
            print(
                f"[vllm-smoke][ERROR] model={definition.id} error={exc}",
                file=sys.stderr,
            )
            continue
        print(
            "[vllm-smoke][OK] "
            f"model={definition.id} "
            f"speech_length={len(speech_text)} "
            f"elapsed_ms={result.elapsed_ms:.1f}"
        )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
