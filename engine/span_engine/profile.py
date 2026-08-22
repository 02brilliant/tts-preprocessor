from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Literal


EngineProfile = Literal["default", "simplified"]

_CURRENT_ENGINE_PROFILE: ContextVar[EngineProfile] = ContextVar(
    "tts_preprocessor_engine_profile",
    default="default",
)


def current_engine_profile() -> EngineProfile:
    return _CURRENT_ENGINE_PROFILE.get()


def uses_general_english_fallbacks() -> bool:
    return current_engine_profile() == "default"


@contextmanager
def engine_profile(profile: EngineProfile) -> Iterator[None]:
    if profile not in {"default", "simplified"}:
        raise ValueError("engine profile must be 'default' or 'simplified'")
    token = _CURRENT_ENGINE_PROFILE.set(profile)
    try:
        yield
    finally:
        _CURRENT_ENGINE_PROFILE.reset(token)


__all__ = [
    "EngineProfile",
    "current_engine_profile",
    "engine_profile",
    "uses_general_english_fallbacks",
]
