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
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.binary_runtime import (
    BinaryRuntimeError,
    resolve_binary_path,
    run_transform_binary,
    run_transform_binary_with_rollout,
)

app = FastAPI()

# Production /api/transform calls the packaged runtime binary. Source imports
# here are limited to server wiring and binary resolution, not transform logic.

# ✅ web과 downloads를 함께 공개
app.mount("/web", StaticFiles(directory="web", html=True), name="web")
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")


class TransformRequest(BaseModel):
    text: str
    rollout_mode: str | None = None
    include_debug: bool = False

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
    payload = {"text": req.text}
    if getattr(req, "rollout_mode", None) is not None:
        payload["rollout_mode"] = req.rollout_mode
        if bool(getattr(req, "include_debug", False)):
            payload["include_debug"] = True

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


def transform_request_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")
    if "text" not in payload:
        raise KeyError("text")

    text = payload["text"]
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if "rollout_mode" not in payload:
        return {"normalized_text": run_transform_binary(text)}

    rollout_mode = payload["rollout_mode"]
    include_debug = bool(payload.get("include_debug", False))
    result = run_transform_binary_with_rollout(text, rollout_mode=rollout_mode, include_debug=include_debug)
    if isinstance(result, dict):
        return result if "normalized_text" in result else {"normalized_text": result}
    return {"normalized_text": result}


def main() -> None:
    host = os.getenv("TTS_PREPROCESSOR_HOST", "0.0.0.0")
    port = int(os.getenv("TTS_PREPROCESSOR_PORT", "8010"))
    binary_path = resolve_binary_path()
    print(f"Using runtime binary: {binary_path}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
