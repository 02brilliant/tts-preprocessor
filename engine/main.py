from engine.pipeline.transform_engine import normalize_text, transform_text
from engine.prosody.comma import insert_commas
from engine.prosody.paragraph import split_paragraphs


def transform(text: str) -> str:
    """
    Full TTS preprocessing pipeline

    1. normalize
    2. comma insertion
    3. paragraph segmentation
    """
    normalized = normalize_text(text)
    text = insert_commas(normalized)
    text = split_paragraphs(text)
    return text


def transform_with_rollout(
    text: str,
    *,
    mode: str = "legacy_default",
    include_debug: bool = False,
    legacy_transform=None,
):
    """Run rollout modes; span_default is the official source-side production entrypoint."""
    from engine.span_engine.production_adapter import run_rollout_transform

    legacy_callable = legacy_transform if legacy_transform is not None else transform
    result = run_rollout_transform(
        text,
        mode=mode,
        legacy_transform=legacy_callable,
        include_debug=include_debug,
    )

    if not result["ok"]:
        if _is_text_content_internal_error(result):
            fallback = _preserve_original_fallback(text, result)
            return fallback if include_debug else fallback["normalized_text"]
        if include_debug:
            return result
        raise RuntimeError(result["error"] or "rollout transform failed")

    if include_debug:
        return result

    return result["normalized_text"]


def _is_text_content_internal_error(result) -> bool:
    if not isinstance(result, dict):
        return False
    return result.get("mode") == "span_default" and bool(result.get("error"))


def _preserve_original_fallback(text: str, result: dict) -> dict:
    error_message = str(result.get("error") or "transform failed")
    return {
        **result,
        "ok": True,
        "normalized_text": text,
        "production_output": text,
        "span_output": text,
        "fallback": "preserve_original",
        "error_type": "RuntimeError",
        "error_message": error_message,
        "error_stage": "transform",
        "error": None,
    }
