import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the simplified TTS preprocessor with file, text, or stdin input."
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


def run() -> int:
    from engine.main import transform_simplified, transform_simplified_debug

    args = parse_args()
    text = _read_input_text(args)
    result = (
        transform_simplified_debug(text)
        if args.include_debug
        else transform_simplified(text)
    )
    output_text = json.dumps(result, ensure_ascii=False) if args.include_debug else result
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
    else:
        print(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
