from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, model_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.binary_runtime import (
    BinaryRuntimeError,
    resolve_binary_path,
    run_transform_binary,
    run_transform_binary_debug,
)
from LLM.client import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUpstreamHTTPError,
)
from LLM.config import (
    ConfigurationError,
    load_model_config,
)
from LLM import stage_engine
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
from LLM.prompt_template import (
    PromptTemplateError,
)
from LLM.response_validation import (
    LLMStageContractError,
)
from LLM.stage_engine import UnsupportedLLMModelError

app = FastAPI()

# Production /api/transform calls the packaged runtime binary. LLM support is
# isolated under LLM/ and routes only to the selected configured provider.

# ✅ web과 downloads를 함께 공개
app.mount("/web", StaticFiles(directory="web", html=True), name="web")
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")


class TransformRequest(BaseModel):
    text: str
    include_debug: bool = False

    @model_validator(mode="before")
    @classmethod
    def reject_removed_rollout_field(cls, value):
        if isinstance(value, dict) and "rollout_mode" in value:
            raise ValueError(
                "rollout_mode is no longer supported by the production API"
            )
        return value


class LLMTransformRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_text: str
    model: str | None = None


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ root는 web으로 보내기
@app.get("/")
def root():
    return RedirectResponse("/web/")


@app.post("/api/transform")
def transform_api(req: TransformRequest) -> dict:
    payload = {"text": req.text, "include_debug": req.include_debug}

    try:
        result = transform_request_payload(payload)
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except BinaryRuntimeError as exc:
        error_message = str(exc).strip() or "실행모듈 호출에 실패했습니다."
        raise HTTPException(status_code=500, detail=error_message) from exc
    except Exception as exc:
        error_message = str(exc).strip() or "정규화 처리에 실패했습니다."
        raise HTTPException(status_code=500, detail=error_message) from exc

    normalized_text = result.get("normalized_text")
    if not normalized_text:
        raise HTTPException(status_code=500, detail="정규화 결과가 비어 있습니다.")
    return result


@app.get("/api/llm/models")
def llm_models_api() -> dict:
    try:
        model_config = load_model_config()
    except ConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "models": list(model_config.models),
        "default_model": model_config.default_model,
    }


@app.api_route("/api/llm/transform", methods=["POST"])
def llm_transform_api(req: LLMTransformRequest) -> dict:
    try:
        result = stage_engine.transform(req.normalized_text, model=req.model)
    except UnsupportedLLMModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PromptTemplateError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except (LLMConnectionError, LLMUpstreamHTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except LLMStageContractError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(exc),
                "stage": exc.stage,
                f"{exc.stage}_text": exc.output_text,
            },
        ) from exc
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GeminiTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except GeminiRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except GeminiServiceDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GeminiAPIKeyRestrictionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (
        GeminiAuthenticationError,
        GeminiConnectionError,
        GeminiUpstreamHTTPError,
        GeminiResponseError,
    ) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except OpenAITimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except OpenAIRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except OpenAIPermissionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (
        OpenAIAuthenticationError,
        OpenAIConnectionError,
        OpenAIUpstreamHTTPError,
        OpenAIResponseError,
    ) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "speech_text": result.speech_text,
        "model": result.model,
        "elapsed_ms": round(result.elapsed_ms, 3),
    }


def transform_request_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")
    if "text" not in payload:
        raise KeyError("text")
    if "rollout_mode" in payload:
        raise ValueError(
            "rollout_mode is not supported by the production API; "
            "use engine.main.transform or engine.main.transform_debug"
        )

    text = payload["text"]
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    include_debug = payload.get("include_debug", False)
    if not isinstance(include_debug, bool):
        raise TypeError("include_debug must be bool")

    if include_debug:
        result = run_transform_binary_debug(text)
        return result if "normalized_text" in result else {"normalized_text": result}
    return {"normalized_text": run_transform_binary(text)}


def main() -> None:
    host = os.getenv("TTS_PREPROCESSOR_HOST", "0.0.0.0")
    port = int(os.getenv("TTS_PREPROCESSOR_PORT", "8010"))
    binary_path = resolve_binary_path()
    print(f"Using runtime binary: {binary_path}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
