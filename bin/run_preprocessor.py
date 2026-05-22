import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.binary_runtime import BinaryRuntimeError, run_transform_binary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the packaged TTS preprocessor binary with file, text, or stdin input."
    )
    parser.add_argument("--input", help="Input file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--text", help="Text to preprocess directly")
    return parser.parse_args()


def run() -> int:
    args = parse_args()

    if args.text is not None:
        text = args.text
    elif args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    try:
        result = run_transform_binary(text)
    except (BinaryRuntimeError, FileNotFoundError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
