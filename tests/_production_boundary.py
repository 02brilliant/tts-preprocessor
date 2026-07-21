from __future__ import annotations

from collections.abc import Iterable


ALLOWED_BINARY_MODULE_PREFIXES = (
    "engine.span_engine",
)

ALLOWED_BINARY_MODULES = (
    "engine.main",
    "engine.prosody",
    "engine.prosody.paragraph",
)

REQUIRED_BINARY_MODULES = (
    "engine.main",
    "engine.prosody.paragraph",
    "engine.span_engine.production_adapter",
    "engine.span_engine.trace",
    "engine.span_engine.transform",
)


def unexpected_binary_modules(modules: Iterable[str]) -> list[str]:
    return sorted(
        module
        for module in modules
        if module not in ALLOWED_BINARY_MODULES
        and not any(
            module == prefix or module.startswith(prefix + ".")
            for prefix in ALLOWED_BINARY_MODULE_PREFIXES
        )
    )
