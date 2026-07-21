from __future__ import annotations


def test_phase20e_engine_main_transform_exists_and_returns_string() -> None:
    import engine.main

    assert callable(engine.main.transform)
    assert isinstance(engine.main.transform("AI"), str)
    assert isinstance(engine.main.transform("안녕하세요"), str)


def test_phase20e_engine_api_interface_wraps_canonical_facade() -> None:
    from engine.api_interface import normalize_text
    from engine.main import transform

    assert normalize_text(None) == ""
    assert normalize_text("") == ""
    assert normalize_text("AI") == transform("AI")
