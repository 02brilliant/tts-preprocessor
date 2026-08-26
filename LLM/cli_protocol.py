from __future__ import annotations

from typing import Any

from LLM.config import ConfigurationError
from LLM.prompt_template import PromptTemplateError
from LLM.response_validation import LLMStageContractError
from LLM.stage_engine import UnsupportedLLMModelError
from LLM.client import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUpstreamHTTPError,
)
from LLM.gemini_client import (
    GeminiAPIKeyRestrictionError,
    GeminiAuthenticationError,
    GeminiConnectionError,
    GeminiRateLimitError,
    GeminiResponseError,
    GeminiServiceDisabledError,
    GeminiTimeoutError,
    GeminiUpstreamHTTPError,
)
from LLM.openai_client import (
    OpenAIAuthenticationError,
    OpenAIConnectionError,
    OpenAIPermissionError,
    OpenAIRateLimitError,
    OpenAIResponseError,
    OpenAITimeoutError,
    OpenAIUpstreamHTTPError,
)
from LLM.vllm_client import (
    VllmAuthenticationError,
    VllmConnectionError,
    VllmPermissionError,
    VllmRateLimitError,
    VllmResponseError,
    VllmTimeoutError,
    VllmUpstreamHTTPError,
)


def classify_llm_stage_error(exc: BaseException) -> tuple[int, Any]:
    """Map a stage-2 exception to an HTTP status and API detail payload."""

    if isinstance(exc, UnsupportedLLMModelError):
        return 400, str(exc)
    if isinstance(exc, ConfigurationError):
        return 503, str(exc)
    if isinstance(exc, PromptTemplateError):
        return 500, str(exc)
    if isinstance(
        exc,
        (
            LLMTimeoutError,
            GeminiTimeoutError,
            OpenAITimeoutError,
            VllmTimeoutError,
        ),
    ):
        return 504, str(exc)
    if isinstance(
        exc,
        (
            GeminiRateLimitError,
            OpenAIRateLimitError,
            VllmRateLimitError,
        ),
    ):
        return 429, str(exc)
    if isinstance(
        exc,
        (
            OpenAIPermissionError,
            VllmPermissionError,
            GeminiServiceDisabledError,
            GeminiAPIKeyRestrictionError,
        ),
    ):
        return 503, str(exc)
    if isinstance(exc, LLMStageContractError):
        detail = {
            "message": str(exc),
            "stage": exc.stage,
            f"{exc.stage}_text": exc.output_text,
        }
        if exc.output_start is not None and exc.output_end is not None:
            detail["validation_failure"] = {
                "code": exc.code,
                "severity": exc.severity,
                "message": str(exc),
                "output_start": exc.output_start,
                "output_end": exc.output_end,
            }
        return 502, detail
    if isinstance(
        exc,
        (
            LLMConnectionError,
            LLMUpstreamHTTPError,
            LLMResponseError,
            GeminiAuthenticationError,
            GeminiConnectionError,
            GeminiUpstreamHTTPError,
            GeminiResponseError,
            OpenAIAuthenticationError,
            OpenAIConnectionError,
            OpenAIUpstreamHTTPError,
            OpenAIResponseError,
            VllmAuthenticationError,
            VllmConnectionError,
            VllmUpstreamHTTPError,
            VllmResponseError,
        ),
    ):
        return 502, str(exc)
    return 500, str(exc).strip() or "LLM stage failed."
