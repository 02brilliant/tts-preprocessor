from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT_DIR = Path(__file__).resolve().parent.parent
PACKAGES_DIR = ROOT_DIR / "packages"
DOWNLOADS_DIR = ROOT_DIR / "downloads"
PACKAGE_NAME = "tts-preprocessor"
ARCHIVE_NAME = "tts-preprocessor-linux.zip"
DEFAULT_BINARY_PATH = ROOT_DIR / "dist" / "tts_preprocessor"
DEFAULT_SIMPLIFIED_BINARY_PATH = ROOT_DIR / "dist" / "tts-preprocessor-simplified"
DEFAULT_LLM_MINIMAL_BINARY_PATH = ROOT_DIR / "dist" / "tts-preprocessor-llm-minimal"
DEFAULT_LLM_NATURAL_BINARY_PATH = ROOT_DIR / "dist" / "tts-preprocessor-llm-natural"
README_TEMPLATE_PATH = ROOT_DIR / "docs" / "Release_Package_README.txt"


def build_readme() -> str:
    if not README_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Missing README template: {README_TEMPLATE_PATH}")

    return README_TEMPLATE_PATH.read_text(encoding="utf-8")


def build_package(
    binary_path: Path = DEFAULT_BINARY_PATH,
    simplified_binary_path: Path = DEFAULT_SIMPLIFIED_BINARY_PATH,
    llm_minimal_binary_path: Path = DEFAULT_LLM_MINIMAL_BINARY_PATH,
    llm_natural_binary_path: Path = DEFAULT_LLM_NATURAL_BINARY_PATH,
) -> Path:
    package_dir = PACKAGES_DIR / PACKAGE_NAME
    archive_path = DOWNLOADS_DIR / ARCHIVE_NAME

    prepared_binary = resolve_binary_path(binary_path)
    prepared_simplified_binary = resolve_binary_path(simplified_binary_path)
    prepared_llm_minimal_binary = resolve_binary_path(llm_minimal_binary_path)
    prepared_llm_natural_binary = resolve_binary_path(llm_natural_binary_path)
    require_prepared_binary(prepared_binary)
    require_prepared_binary(prepared_simplified_binary)
    require_prepared_binary(prepared_llm_minimal_binary)
    require_prepared_binary(prepared_llm_natural_binary)
    remove_previous_artifacts(package_dir)
    create_package_structure(
        package_dir,
        prepared_binary,
        prepared_simplified_binary,
        prepared_llm_minimal_binary,
        prepared_llm_natural_binary,
    )
    validate_package_structure(package_dir)
    create_archive_atomically(package_dir, archive_path)

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


def remove_previous_artifacts(current_package_dir: Path) -> None:
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    if current_package_dir.exists():
        shutil.rmtree(current_package_dir)


def create_package_structure(
    package_dir: Path,
    binary_path: Path,
    simplified_binary_path: Path,
    llm_minimal_binary_path: Path,
    llm_natural_binary_path: Path,
) -> None:
    if package_dir.exists():
        shutil.rmtree(package_dir)

    package_dir.mkdir(parents=True, exist_ok=True)

    (package_dir / "README.txt").write_text(build_readme(), encoding="utf-8")
    binary_target = package_dir / "tts-preprocessor"
    shutil.copy2(binary_path, binary_target)
    binary_target.chmod(0o755)
    simplified_target = package_dir / "tts-preprocessor-simplified"
    shutil.copy2(simplified_binary_path, simplified_target)
    simplified_target.chmod(0o755)
    llm_minimal_target = package_dir / "tts-preprocessor-llm-minimal"
    shutil.copy2(llm_minimal_binary_path, llm_minimal_target)
    llm_minimal_target.chmod(0o755)
    llm_natural_target = package_dir / "tts-preprocessor-llm-natural"
    shutil.copy2(llm_natural_binary_path, llm_natural_target)
    llm_natural_target.chmod(0o755)


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


def create_archive_atomically(package_dir: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        dir=archive_path.parent,
        prefix=f".{ARCHIVE_NAME}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED) as zip_file:
            for path in sorted(package_dir.rglob("*")):
                if path.is_dir():
                    continue
                zip_file.write(path, path.relative_to(package_dir.parent))

        validate_archive(temporary_path)
        os.replace(temporary_path, archive_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def validate_archive(archive_path: Path) -> None:
    expected_names = {
        "tts-preprocessor/README.txt",
        "tts-preprocessor/tts-preprocessor-llm-minimal",
        "tts-preprocessor/tts-preprocessor-llm-natural",
        "tts-preprocessor/tts-preprocessor",
        "tts-preprocessor/tts-preprocessor-simplified",
    }
    with ZipFile(archive_path) as zip_file:
        corrupt_member = zip_file.testzip()
        if corrupt_member is not None:
            raise RuntimeError(f"Archive contains a corrupt member: {corrupt_member}")
        actual_names = {name for name in zip_file.namelist() if not name.endswith("/")}

    if actual_names != expected_names:
        raise RuntimeError(
            "Unexpected Linux archive contents: "
            f"expected={sorted(expected_names)}, actual={sorted(actual_names)}"
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package an already-built TTS preprocessor binary."
    )
    parser.add_argument(
        "--simplified-binary",
        type=Path,
        default=DEFAULT_SIMPLIFIED_BINARY_PATH,
        help="Prepared simplified binary. Defaults to dist/tts-preprocessor-simplified.",
    )
    parser.add_argument(
        "--binary",
        type=Path,
        default=DEFAULT_BINARY_PATH,
        help="Prepared binary to package. Defaults to dist/tts_preprocessor.",
    )
    parser.add_argument(
        "--llm-minimal-binary",
        type=Path,
        default=DEFAULT_LLM_MINIMAL_BINARY_PATH,
        help="Prepared level-3 binary.",
    )
    parser.add_argument(
        "--llm-natural-binary",
        type=Path,
        default=DEFAULT_LLM_NATURAL_BINARY_PATH,
        help="Prepared level-4 binary.",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        archive_path = build_package(
            args.binary,
            args.simplified_binary,
            args.llm_minimal_binary,
            args.llm_natural_binary,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Created package: {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
