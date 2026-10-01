"""Character coordinates carried by the actual presentation edits.

Indices refer to the joined RenderPieces, not guessed original-input offsets.
Inserted characters have no source index. This is internal metadata only.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MappedText:
    text: str
    indices: tuple[int | None, ...]

    def __post_init__(self) -> None:
        if len(self.text) != len(self.indices):
            raise ValueError("text-coordinate length mismatch")

    @classmethod
    def identity(cls, text: str) -> MappedText:
        return cls(text, tuple(range(len(text))))

    @classmethod
    def inserted(cls, text: str) -> MappedText:
        return cls(text, (None,) * len(text))

    @classmethod
    def join(cls, values, separator: str = "") -> MappedText:
        parts = list(values)
        text = separator.join(part.text for part in parts)
        indices: list[int | None] = []
        for index, part in enumerate(parts):
            if index:
                indices.extend([None] * len(separator))
            indices.extend(part.indices)
        return cls(text, tuple(indices))

    def slice(self, start: int, end: int | None = None) -> MappedText:
        return MappedText(self.text[start:end], self.indices[start:end])

    def strip(self, chars: str | None = None) -> MappedText:
        start = len(self.text) - len(self.text.lstrip(chars))
        end = len(self.text.rstrip(chars))
        return self.slice(start, max(start, end))

    def rstrip(self, chars: str | None = None) -> MappedText:
        return self.slice(0, len(self.text.rstrip(chars)))


def rendered_index_map(output) -> dict[int, int] | None:
    """Use recorded edits or an identity; never align repeated text by search."""
    rendered = "".join(piece.text for piece in output.render_pieces)
    indices = output.rendered_indices
    if indices is None:
        if rendered != output.normalized_text:
            return None
        indices = tuple(range(len(rendered)))
    if len(indices) != len(output.normalized_text):
        return None
    previous = -1
    mapping = {}
    for final_index, rendered_index in enumerate(indices):
        if rendered_index is None:
            continue
        if (rendered_index <= previous or rendered_index >= len(rendered)
                or rendered[rendered_index] != output.normalized_text[final_index]):
            return None
        mapping[rendered_index] = final_index
        previous = rendered_index
    return mapping
