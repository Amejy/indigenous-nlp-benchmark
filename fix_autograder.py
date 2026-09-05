"""Repair the three Nupe assignment autograder issues."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
JSONL_PATH = ROOT / "data/nup/raw/raw_data_group_01.jsonl"
STOP_WORDS_PATH = ROOT / "data/nup/processed/stop_words_group_01.txt"
OLD_SUBMISSION_DIR = ROOT / "submissions/group_01-nup"
NEW_SUBMISSION_DIR = ROOT / "submissions/group_01_nupe"


def atomic_write(path: Path, content: str) -> None:
    """Write content beside the target, then replace the target atomically."""
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent, text=True
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as temporary:
            temporary.write(content)
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def fix_jsonl_ids() -> None:
    print(f"[1/4] Fixing JSONL IDs: {JSONL_PATH.relative_to(ROOT)}")
    if not JSONL_PATH.is_file():
        raise FileNotFoundError(f"Missing file: {JSONL_PATH}")

    fixed_lines: list[str] = []
    record_count = 0
    for line_number, line in enumerate(
        JSONL_PATH.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON on line {line_number}: {error}") from error
        if not isinstance(record, dict):
            raise ValueError(f"Line {line_number} must contain a JSON object")

        record_count += 1
        record["id"] = record_count
        fixed_lines.append(json.dumps(record, ensure_ascii=False))

    atomic_write(JSONL_PATH, "\n".join(fixed_lines) + ("\n" if fixed_lines else ""))
    print(f"      Converted {record_count} IDs to integers (1-{record_count}).")


def fix_stop_words() -> None:
    print(f"[2/4] Replacing tabs: {STOP_WORDS_PATH.relative_to(ROOT)}")
    if not STOP_WORDS_PATH.is_file():
        raise FileNotFoundError(f"Missing file: {STOP_WORDS_PATH}")

    content = STOP_WORDS_PATH.read_text(encoding="utf-8")
    tab_count = content.count("\t")
    atomic_write(STOP_WORDS_PATH, content.replace("\t", " "))
    print(f"      Replaced {tab_count} tab character(s) with spaces.")


def fix_submission_folder() -> None:
    print("[3/4] Checking submission folder name")
    if OLD_SUBMISSION_DIR.is_dir():
        if NEW_SUBMISSION_DIR.exists():
            raise FileExistsError(
                f"Cannot rename: target already exists: {NEW_SUBMISSION_DIR}"
            )
        OLD_SUBMISSION_DIR.rename(NEW_SUBMISSION_DIR)
        print("      Renamed group_01-nup to group_01_nupe.")
    elif NEW_SUBMISSION_DIR.is_dir():
        print("      Folder is already named group_01_nupe.")
    else:
        raise FileNotFoundError(
            "Neither submissions/group_01-nup nor submissions/group_01_nupe exists"
        )

    # Handle a previous partial rename such as group_01_nupe/group_01-nup.
    nested_legacy_dir = NEW_SUBMISSION_DIR / OLD_SUBMISSION_DIR.name
    if nested_legacy_dir.is_dir():
        print("      Found a nested legacy folder; moving its files to the required path.")
        for child in nested_legacy_dir.iterdir():
            if child.is_dir():
                continue
            destination = NEW_SUBMISSION_DIR / child.name
            if destination.exists():
                raise FileExistsError(
                    f"Cannot move {child}: target already exists: {destination}"
                )
            child.rename(destination)
            print(f"      Moved {child.name} into submissions/group_01_nupe.")


def update_path_references() -> None:
    print("[4/4] Updating remaining path references")
    old_name = "group_01-nup"
    new_name = "group_01_nupe"
    updated_files = 0

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path == Path(__file__):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if old_name in content:
            atomic_write(path, content.replace(old_name, new_name))
            updated_files += 1
            print(f"      Updated {path.relative_to(ROOT)}")

    if updated_files == 0:
        print("      No remaining references needed updating.")


def main() -> None:
    print("Starting autograder fixes...\n")
    fix_jsonl_ids()
    fix_stop_words()
    fix_submission_folder()
    update_path_references()
    print("\nAll autograder fixes completed successfully.")


if __name__ == "__main__":
    main()
