from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from engine.span_engine.compare import (
    CompareCorpusEntry,
    resolve_legacy_transform,
    run_compare_corpus,
    run_default_compare_report,
    write_compare_jsonl,
    write_compare_markdown,
)


def parse_compare_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="compare-dry-run")
    parser.add_argument("--input", type=str, default=None)
    parser.add_argument("--jsonl", type=str, default=None)
    parser.add_argument("--markdown", type=str, default=None)
    parser.add_argument("--include-debug", dest="include_debug", action="store_true")
    parser.add_argument("--no-legacy", dest="no_legacy", action="store_true")
    parser.add_argument(
        "--use-default-corpus",
        dest="use_default_corpus",
        action="store_true",
        default=True,
    )
    return parser.parse_args(argv)


def load_compare_entries_from_file(path: str | Path) -> list[CompareCorpusEntry]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".jsonl":
        return _load_compare_entries_from_jsonl(text)
    return _load_compare_entries_from_text(text)


def run_compare_cli(
    argv: list[str],
    legacy_transform: Any | None = None,
    span_transform: Any | None = None,
) -> int:
    args = parse_compare_args(argv)

    if args.input:
        entries = load_compare_entries_from_file(args.input)
        legacy_callable = _resolve_legacy_callable(
            args=args,
            legacy_transform=legacy_transform,
        )
        if legacy_callable is None and args.no_legacy:
            legacy_callable = lambda text: text
        report = run_compare_corpus(
            entries,
            legacy_transform=legacy_callable,
            span_transform=span_transform,
            include_debug=args.include_debug,
        )
    else:
        if legacy_transform is not None:
            legacy_callable = legacy_transform
        elif args.no_legacy:
            legacy_callable = lambda text: text
        else:
            legacy_callable = None

        if legacy_callable is None:
            report = run_default_compare_report(
                span_transform=span_transform,
                include_debug=args.include_debug,
            )
        else:
            report = run_default_compare_report(
                legacy_transform=legacy_callable,
                span_transform=span_transform,
                include_debug=args.include_debug,
            )

    if args.jsonl:
        write_compare_jsonl(report, args.jsonl)
    if args.markdown:
        write_compare_markdown(report, args.markdown, include_debug=args.include_debug)
    return 0


def _resolve_legacy_callable(
    args: argparse.Namespace,
    legacy_transform: Any | None,
) -> Any | None:
    if legacy_transform is not None:
        return legacy_transform
    if args.no_legacy:
        return None
    return resolve_legacy_transform()


def _load_compare_entries_from_text(text: str) -> list[CompareCorpusEntry]:
    entries: list[CompareCorpusEntry] = []
    line_index = 0
    for raw_line in text.splitlines():
        line = raw_line.strip("\n\r")
        if not line.strip():
            continue
        line_index += 1
        entries.append(
            CompareCorpusEntry(
                id=f"line-{line_index}",
                text=line,
                tags=("file", "txt"),
                expected_category=None,
                metadata={"source": "txt", "line": line_index},
            )
        )
    return entries


def _load_compare_entries_from_jsonl(text: str) -> list[CompareCorpusEntry]:
    entries: list[CompareCorpusEntry] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL line {line_no}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"invalid JSONL line {line_no}: expected object")
        if "text" not in data:
            raise ValueError(f"missing text at line {line_no}")

        entry_data = dict(data)
        entry_data.setdefault("id", f"line-{line_no}")
        entries.append(CompareCorpusEntry.from_dict(entry_data))
    return entries


__all__ = [
    "load_compare_entries_from_file",
    "parse_compare_args",
    "run_compare_cli",
]
