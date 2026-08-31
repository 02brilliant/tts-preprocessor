from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
CORE_PROBES = (
    ROOT_DIR / "scripts" / "probes" / "decimal_fractional_zero.py",
    ROOT_DIR / "scripts" / "probes" / "colon_time_like_policy.py",
    ROOT_DIR / "scripts" / "probes" / "large_unit_numeric_surface.py",
    ROOT_DIR / "scripts" / "probes" / "registered_unit_surface.py",
    ROOT_DIR / "scripts" / "probes" / "json_like_protected_spans.py",
    ROOT_DIR / "scripts" / "probes" / "contextual_number_units.py",
    ROOT_DIR / "scripts" / "probes" / "deploy_critical_surface.py",
)
SCENARIO_PROBES = (
    ROOT_DIR / "scripts" / "probes" / "scenario_regression.py",
)
SUITE_CHOICES = ("core", "scenario", "all")
RUNTIME_CHOICES = ("source", "production_source", "binary", "api")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run semantic probe suites through one entrypoint."
    )
    parser.add_argument(
        "--suite",
        choices=SUITE_CHOICES,
        default="core",
        help="Probe suite to run. Defaults to core.",
    )
    parser.add_argument(
        "--runtime",
        choices=RUNTIME_CHOICES,
        help=(
            "Run one explicit runtime. Omit this to preserve each probe's "
            "default runner policy."
        ),
    )
    parser.add_argument(
        "--binary",
        type=Path,
        help="PyInstaller binary path for --runtime binary.",
    )
    parser.add_argument(
        "--api",
        help="API base URL for --runtime api.",
    )
    args = parser.parse_args()

    if args.runtime == "binary" and args.binary is None:
        parser.error("--runtime binary requires --binary PATH")
    if args.runtime == "api" and not args.api:
        parser.error("--runtime api requires --api URL")
    return args


def build_probe_args(args: argparse.Namespace) -> list[str]:
    if args.runtime is None:
        return []

    probe_args = ["--only-runtime", args.runtime]
    if args.runtime == "binary":
        probe_args.extend(["--binary", str(args.binary)])
    elif args.runtime == "api":
        probe_args.extend(["--api", args.api])
    return probe_args


def run_probe(probe_path: Path, probe_args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(probe_path), *probe_args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )


def select_probes(suite: str) -> tuple[Path, ...]:
    if suite == "core":
        return CORE_PROBES
    if suite == "scenario":
        return SCENARIO_PROBES
    if suite == "all":
        return (*CORE_PROBES, *SCENARIO_PROBES)
    raise ValueError(f"unsupported suite: {suite}")


def main() -> int:
    args = parse_args()
    probe_args = build_probe_args(args)
    failed_probes: list[tuple[Path, int]] = []

    runtime_label = args.runtime or "default"
    probe_paths = select_probes(args.suite)
    print(f"[semantic-probes] Running {args.suite} suite (runtime={runtime_label})")

    for probe_path in probe_paths:
        if not probe_path.exists():
            print(f"[semantic-probes][FAIL] missing probe: {probe_path}", file=sys.stderr)
            failed_probes.append((probe_path, 1))
            continue

        print(f"[semantic-probes] Probe: {probe_path.name}")
        result = run_probe(probe_path, probe_args)
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(
                result.stderr,
                file=sys.stderr,
                end="" if result.stderr.endswith("\n") else "\n",
            )
        if result.returncode != 0:
            failed_probes.append((probe_path, result.returncode))

    if failed_probes:
        print("[semantic-probes][FAIL] Failed probes:", file=sys.stderr)
        for probe_path, returncode in failed_probes:
            print(
                f"  - {probe_path.name} (exit {returncode})",
                file=sys.stderr,
            )
        return 1

    print(f"[semantic-probes][OK] {args.suite} semantic probe suite passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
