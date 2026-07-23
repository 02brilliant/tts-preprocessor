from __future__ import annotations

import importlib


def test_phase19d_load_compare_entries_from_text_file(tmp_path) -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    load_compare_entries_from_file = getattr(compare_cli, "load_compare_entries_from_file")

    path = tmp_path / "cases.txt"
    path.write_text("안녕하세요\n\n3~8cm\n그리고 우리는 결과를 확인했다\n", encoding="utf-8")

    entries = load_compare_entries_from_file(path)

    assert len(entries) == 3
    assert [entry.id for entry in entries] == ["line-1", "line-2", "line-3"]
    assert [entry.text for entry in entries] == [
        "안녕하세요",
        "3~8cm",
        "그리고 우리는 결과를 확인했다",
    ]


def test_phase19d_load_compare_entries_from_jsonl_file(tmp_path) -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    load_compare_entries_from_file = getattr(compare_cli, "load_compare_entries_from_file")

    path = tmp_path / "cases.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"id":"same-ai","text":"AI","tags":["canonical"],"metadata":{"source":"jsonl"}}',
                '{"id":"range","text":"3~8cm","tags":["range","intended_diff"],"expected_category":"intended_v5_change"}',
            ]
        ),
        encoding="utf-8",
    )

    entries = load_compare_entries_from_file(path)

    assert [entry.id for entry in entries] == ["same-ai", "range"]
    assert [entry.text for entry in entries] == ["AI", "3~8cm"]
    assert entries[0].metadata == {"source": "jsonl"}
    assert entries[1].expected_category == "intended_v5_change"


def test_phase19d_load_compare_entries_from_jsonl_invalid_line_reports_line_number(tmp_path) -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    load_compare_entries_from_file = getattr(compare_cli, "load_compare_entries_from_file")

    path = tmp_path / "bad.jsonl"
    path.write_text('{"id":"ok","text":"AI"}\nnot-json\n', encoding="utf-8")

    try:
        load_compare_entries_from_file(path)
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
    else:
        raise AssertionError("expected failure for invalid JSONL line")

    assert "2" in message or "line 2" in message

