from __future__ import annotations


def test_phase20f_api_interface_normalize_text_exists_and_returns_string() -> None:
    from engine import api_interface

    assert callable(api_interface.normalize_text)
    output = api_interface.normalize_text("AI")
    assert isinstance(output, str)
    assert output


def test_phase20f_api_interface_current_default_matches_canonical_facade() -> None:
    from engine.api_interface import normalize_text
    from engine.main import transform

    assert normalize_text("90km/h") == transform("90km/h")
    assert normalize_text("그리고 우리는 결과를 확인했다") == transform("그리고 우리는 결과를 확인했다")
