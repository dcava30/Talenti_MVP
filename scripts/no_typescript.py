#!/usr/bin/env python3
"""Fail the check if any TypeScript files remain in the repository."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
}


def iter_typescript_files(root: Path) -> Iterable[Path]:
    """Yield any .ts or .tsx files under the provided root."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            if filename.endswith((".ts", ".tsx")):
                yield Path(dirpath) / filename


def main() -> int:
    """Run the TypeScript scan and return a process exit code."""
    root = Path(__file__).resolve().parents[1]
    matches = sorted(iter_typescript_files(root))
    if matches:
        print("TypeScript files detected. Please remove or convert them:")
        for match in matches:
            print(f"- {match.relative_to(root)}")
        return 1
    print("No TypeScript files found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
