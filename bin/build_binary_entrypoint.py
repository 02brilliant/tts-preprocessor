import argparse
import json
import sys
from pathlib import Path


# PyInstaller/CLI runtime entrypoint. All production calls route through the
# mode-less engine.main span facade.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the TTS preprocessor with file, text, or stdin input."
    )
    parser.add_argument("--input", help="Input file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--text", help="Text to preprocess directly")
    parser.add_argument(
        "--include-debug",
        action="store_true",
        help="Emit structured span debug JSON.",
    )
    return parser.parse_args()


def _read_input_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.input:
        return Path(args.input).read_text(encoding="utf-8")
    return sys.stdin.read()


def _serialize_result(result, *, include_debug: bool) -> str:
    if include_debug:
        return json.dumps(result, ensure_ascii=False)
    return result


def _write_output(output_text: str, *, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(output_text, encoding="utf-8")
        return
    print(output_text)


def run() -> int:
    from engine.main import transform, transform_debug

    args = parse_args()
    text = _read_input_text(args)
    result = transform_debug(text) if args.include_debug else transform(text)
    _write_output(
        _serialize_result(result, include_debug=args.include_debug),
        output_path=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
