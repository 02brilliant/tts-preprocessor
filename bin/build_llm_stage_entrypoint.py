from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run stage-2 LLM TTS pronunciation correction."
    )
    parser.add_argument("--input", help="Stage-1 output text file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--text", help="Stage-1 output to process directly")
    parser.add_argument("--model", help="Configured LLM model ID")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate bundled prompt and model assets without calling an LLM.",
    )
    return parser.parse_args()


def _read_input_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.input:
        return Path(args.input).read_text(encoding="utf-8")
    return sys.stdin.read()


def _write_output(output_text: str, *, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(output_text, encoding="utf-8")
        return
    print(output_text)


def run() -> int:
    from LLM.stage_engine import transform, validate_runtime_assets

    args = parse_args()
    try:
        if args.check:
            validate_runtime_assets()
            print("LLM stage runtime ready.")
            return 0
        result = transform(_read_input_text(args), model=args.model)
    except Exception as exc:
        print(f"LLM stage failed: {exc}", file=sys.stderr)
        return 1

    _write_output(result.speech_text, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
