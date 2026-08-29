from __future__ import annotations


SPOKEN_NUMERIC_BOUNDARY = "-"


def join_spoken_numeric_boundary(left: str, right: str) -> str:
    """Join a confirmed numeric reading to its spoken suffix boundary."""
    if not isinstance(left, str) or not isinstance(right, str):
        raise TypeError("left and right must be str")
    return f"{left}{SPOKEN_NUMERIC_BOUNDARY}{right}"


def trailing_spoken_numeric_boundary(reading: str) -> str:
    """Append the canonical boundary for an original suffix rendered later."""
    if not isinstance(reading, str):
        raise TypeError("reading must be str")
    return f"{reading}{SPOKEN_NUMERIC_BOUNDARY}"


__all__ = [
    "SPOKEN_NUMERIC_BOUNDARY",
    "join_spoken_numeric_boundary",
    "trailing_spoken_numeric_boundary",
]
