from __future__ import annotations

import sys

from LLM.config import ConfigurationError, load_gemini_settings, load_model_config
from LLM.gemini_client import GeminiClientError, generate_gemini
from LLM.prompt_template import PromptTemplateError, build_prompt


SMOKE_INPUT = "AI는 3kg 제품을 소개했다."


def main() -> int:
    try:
        settings = load_gemini_settings()
        model_config = load_model_config()
        prompt = build_prompt(SMOKE_INPUT)
    except (ConfigurationError, PromptTemplateError) as exc:
        print(f"[gemini-smoke][ERROR] {exc}", file=sys.stderr)
        return 1

    failed = False
    for definition in model_config.definitions:
        if definition.provider != "gemini":
            continue
        try:
            result = generate_gemini(
                model=definition.upstream_model,
                prompt=prompt,
                settings=settings,
            )
        except GeminiClientError as exc:
            failed = True
            print(
                f"[gemini-smoke][ERROR] model={definition.id} error={exc}",
                file=sys.stderr,
            )
            continue
        print(
            "[gemini-smoke][OK] "
            f"model={definition.id} "
            f"response_type=str response_length={len(result.text)} "
            f"elapsed_ms={result.elapsed_ms:.1f}"
        )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
