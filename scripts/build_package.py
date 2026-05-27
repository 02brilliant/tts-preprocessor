from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT_DIR = Path(__file__).resolve().parent.parent
PACKAGES_DIR = ROOT_DIR / "packages"
DOWNLOADS_DIR = ROOT_DIR / "downloads"
PACKAGE_NAME = "tts-preprocessor"
ARCHIVE_NAME = "tts-preprocessor.zip"
DEFAULT_BINARY_PATH = ROOT_DIR / "dist" / "tts_preprocessor"
README_TEMPLATE_PATH = ROOT_DIR / "docs" / "Release_Package_README.txt"


def build_readme() -> str:
    if not README_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Missing README template: {README_TEMPLATE_PATH}")

    return README_TEMPLATE_PATH.read_text(encoding="utf-8")


def build_package(binary_path: Path = DEFAULT_BINARY_PATH) -> Path:
    package_dir = PACKAGES_DIR / PACKAGE_NAME
    archive_path = DOWNLOADS_DIR / ARCHIVE_NAME

    prepared_binary = resolve_binary_path(binary_path)
    require_prepared_binary(prepared_binary)
    remove_previous_artifacts(package_dir, archive_path)
    create_package_structure(package_dir, prepared_binary)
    validate_package_structure(package_dir)
    create_archive(package_dir, archive_path)

    return archive_path


def resolve_binary_path(binary_path: Path) -> Path:
    expanded = binary_path.expanduser()
    if expanded.is_absolute():
        return expanded
    return ROOT_DIR / expanded


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def require_prepared_binary(binary_path: Path) -> None:
    if not binary_path.is_file():
        raise FileNotFoundError(
            f"Missing binary: {display_path(binary_path)}\n"
            "Run `bash scripts/build_binary.sh` first, or pass `--binary <path>`."
        )


def remove_previous_artifacts(current_package_dir: Path, current_archive_path: Path) -> None:
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    for path in PACKAGES_DIR.iterdir():
        if path == current_package_dir:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    for path in DOWNLOADS_DIR.iterdir():
        if path == current_archive_path:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def create_package_structure(package_dir: Path, binary_path: Path) -> None:
    if package_dir.exists():
        shutil.rmtree(package_dir)

    bin_dir = package_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    (package_dir / "README.txt").write_text(build_readme(), encoding="utf-8")
    binary_target = bin_dir / "tts_preprocessor"
    shutil.copy2(binary_path, binary_target)
    binary_target.chmod(0o755)


def validate_package_structure(package_dir: Path) -> None:
    forbidden_paths: list[str] = []

    for path in sorted(package_dir.rglob("*")):
        relative = path.relative_to(package_dir)
        relative_text = str(relative)

        if path.is_dir() and relative.parts and relative.parts[0] in {"engine", "docs", "tests"}:
            forbidden_paths.append(relative_text)
            continue

        if path.is_file() and path.suffix == ".py":
            forbidden_paths.append(relative_text)

    if forbidden_paths:
        joined = ", ".join(forbidden_paths)
        raise RuntimeError(f"Package contains forbidden source artifacts: {joined}")


def create_archive(package_dir: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for path in sorted(package_dir.rglob("*")):
            if path.is_dir():
                continue
            zip_file.write(path, path.relative_to(package_dir.parent))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package an already-built TTS preprocessor binary."
    )
    parser.add_argument(
        "ignored_version",
        nargs="?",
        help="Deprecated compatibility argument; ignored.",
    )
    parser.add_argument(
        "--binary",
        type=Path,
        default=DEFAULT_BINARY_PATH,
        help="Prepared binary to package. Defaults to dist/tts_preprocessor.",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        archive_path = build_package(args.binary)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Created package: {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
