from engine.main import transform, transform_with_rollout


def normalize_text(text: str) -> str:
    """Return normalized text for TTS server integrations.

    This wrapper is intended for direct use by the TTS server layer when it
    needs to convert raw input text into a pronunciation-friendly form.
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if text == "":
        return ""

    return transform(text)


def normalize_text_with_rollout(
    text: str,
    *,
    mode: str = "legacy_default",
    include_debug: bool = False,
    legacy_transform=None,
):
    return transform_with_rollout(
        text,
        mode=mode,
        include_debug=include_debug,
        legacy_transform=legacy_transform,
    )
