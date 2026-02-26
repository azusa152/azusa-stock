#!/usr/bin/env python3
"""
Locale key parity checker.

Verifies that all locale files within each set (backend and frontend) contain
exactly the same set of keys. Any key present in one locale but missing from
another is reported as an error, and the script exits with a non-zero status.

Usage:
    python scripts/check_locale_parity.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LOCALE_SETS = [
    {
        "name": "backend",
        "directory": REPO_ROOT / "backend" / "i18n" / "locales",
        "glob": "*.json",
    },
    {
        "name": "frontend",
        "directory": REPO_ROOT / "frontend-react" / "public" / "locales",
        "glob": "*.json",
    },
]


def _flatten_keys(obj: dict, prefix: str = "") -> set[str]:
    """Recursively collect all leaf key paths from a nested dict."""
    keys: set[str] = set()
    for k, v in obj.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys |= _flatten_keys(v, full)
        else:
            keys.add(full)
    return keys


def check_set(name: str, directory: Path, glob: str) -> list[str]:
    """Return a list of error messages for missing keys within a locale set."""
    locale_files = sorted(directory.glob(glob))
    if not locale_files:
        return [f"[{name}] No locale files found in {directory}"]

    locales: dict[str, set[str]] = {}
    for path in locale_files:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        locales[path.stem] = _flatten_keys(data)

    # Union of all keys across every locale is the expected complete set.
    all_keys: set[str] = set()
    for keys in locales.values():
        all_keys |= keys

    errors: list[str] = []
    for locale, keys in sorted(locales.items()):
        missing = all_keys - keys
        if missing:
            for key in sorted(missing):
                errors.append(f"[{name}/{locale}] Missing key: {key}")

    return errors


def main() -> int:
    all_errors: list[str] = []
    for spec in LOCALE_SETS:
        errors = check_set(spec["name"], spec["directory"], spec["glob"])
        all_errors.extend(errors)

    if all_errors:
        print("Locale parity check FAILED — missing keys detected:\n", file=sys.stderr)
        for err in all_errors:
            print(f"  {err}", file=sys.stderr)
        print(
            f"\n{len(all_errors)} issue(s) found. "
            "Add the missing keys to every locale file before committing.",
            file=sys.stderr,
        )
        return 1

    locale_counts = {spec["name"]: len(list(Path(spec["directory"]).glob(spec["glob"]))) for spec in LOCALE_SETS}
    total_checked = sum(locale_counts.values())
    print(
        f"Locale parity check PASSED — {total_checked} locale files checked "
        f"({', '.join(f'{v} {k}' for k, v in locale_counts.items())})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
