from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.binary_runtime import (
    BinaryRuntimeError,
    LLMStageRuntimeError,
    list_llm_models,
    resolve_binary_path,
    resolve_integrated_binary_path,
    resolve_simplified_binary_path,
    run_integrated_binary,
    run_transform_binary,
    run_transform_binary_debug,
)

app = FastAPI()

# Production transform requests call exactly one packaged binary for levels 1-5.
# LLM provider credentials stay in process environment from llm.env.

# ✅ web과 downloads를 함께 공개
app.mount("/web", StaticFiles(directory="web", html=True), name="web")
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")


class TransformRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    level: Literal[0, 1, 2, 3, 4, 5] = 2
    model: str | None = None
    include_debug: bool = False

    @model_validator(mode="before")
    @classmethod
    def reject_removed_rollout_field(cls, value):
        if isinstance(value, dict) and "rollout_mode" in value:
            raise ValueError(
                "rollout_mode is no longer supported by the production API"
            )
        return value


    @field_validator("level", mode="before")
    @classmethod
    def reject_non_integer_level(cls, value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("level must be an integer from 0 to 5")
        return value

    @model_validator(mode="after")
    def validate_level_options(self):
        if self.include_debug and self.level not in {1, 2}:
            raise ValueError("include_debug is supported only for levels 1 and 2")
        if self.model is not None and self.level not in {3, 4, 5}:
            raise ValueError("model is supported only for levels 3, 4, and 5")
        return self


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
    payload = {
        "text": req.text,
        "level": req.level,
        "model": req.model,
        "include_debug": req.include_debug,
    }

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
    except LLMStageRuntimeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
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
        return list_llm_models()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except BinaryRuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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

    level = payload.get("level", 2)
    if isinstance(level, bool) or level not in {0, 1, 2, 3, 4, 5}:
        raise ValueError("level must be an integer from 0 to 5")
    model = payload.get("model")
    if model is not None and not isinstance(model, str):
        raise TypeError("model must be str or None")

    if level == 0:
        return {"normalized_text": text}

    if level in {3, 4, 5}:
        if include_debug:
            raise ValueError("include_debug is supported only for levels 1 and 2")
        result = run_integrated_binary(text, level=level, model=model)
        return result

    if model is not None:
        raise ValueError("model is supported only for levels 3, 4, and 5")

    if include_debug:
        result = (
            run_transform_binary_debug(text, profile="simplified")
            if level == 1
            else run_transform_binary_debug(text)
        )
        result = result if "normalized_text" in result else {"normalized_text": result}
        return result
    return {
        "normalized_text": (
            run_transform_binary(text, profile="simplified")
            if level == 1
            else run_transform_binary(text)
        ),
    }


def main() -> None:
    host = os.getenv("TTS_PREPROCESSOR_HOST", "0.0.0.0")
    port = int(os.getenv("TTS_PREPROCESSOR_PORT", "8010"))
    binary_path = resolve_binary_path()
    simplified_binary_path = resolve_simplified_binary_path()
    llm_minimal_binary_path = resolve_integrated_binary_path(3)
    llm_natural_binary_path = resolve_integrated_binary_path(4)
    llm_pronunciation_binary_path = resolve_integrated_binary_path(5)
    print(f"Using runtime binary: {binary_path}")
    print(f"Using simplified runtime binary: {simplified_binary_path}")
    print(f"Using level-3 integrated binary: {llm_minimal_binary_path}")
    print(f"Using level-4 integrated binary: {llm_natural_binary_path}")
    print(f"Using experimental level-5 integrated binary: {llm_pronunciation_binary_path}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
