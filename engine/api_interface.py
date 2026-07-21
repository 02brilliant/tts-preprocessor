from engine.main import transform, transform_debug


def normalize_text(text: str) -> str:
    """Return normalized text for TTS server integrations."""
    if text is None:
        return ""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if text == "":
        return ""
    return transform(text)


def normalize_text_debug(text: str) -> dict:
    """Return normalized text with the canonical span debug payload."""
    if text is None:
        text = ""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return transform_debug(text)


__all__ = ["normalize_text", "normalize_text_debug"]
