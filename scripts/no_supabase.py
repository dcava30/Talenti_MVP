"""Report Supabase references in the repository (warning-only)."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable


FORBIDDEN_TOKENS = ("supabase", "supabase-js", "functions.invoke", "SUPABASE_")
SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "dist-ssr",
    ".venv",
    "__pycache__",
    ".pytest_cache",
}


@dataclass(frozen=True)
class Match:
    """Represents a forbidden token match in a file."""

    path: Path
    line_no: int
    line: str


def iter_files(root: Path) -> Iterable[Path]:
    """Yield files under root while skipping known generated directories."""

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for filename in filenames:
            yield Path(dirpath) / filename


def scan_file(path: Path) -> list[Match]:
    """Scan a single file for forbidden tokens."""

    matches: list[Match] = []
    try:
        contents = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        print(f"Warning: could not read {path}: {exc}")
        return matches

    for line_no, line in enumerate(contents.splitlines(), start=1):
        if any(token in line for token in FORBIDDEN_TOKENS):
            matches.append(Match(path=path, line_no=line_no, line=line.strip()))

    return matches


def main() -> int:
    """Run the Supabase reference scan and print a report."""

    root = Path(__file__).resolve().parents[1]
    all_matches: list[Match] = []

    for file_path in iter_files(root):
        all_matches.extend(scan_file(file_path))

    if not all_matches:
        print("No Supabase references found.")
        return 0

    print("Supabase references found (warning-only):")
    for match in all_matches:
        rel_path = match.path.relative_to(root)
        print(f"- {rel_path}:{match.line_no}: {match.line}")

    print(f"Total matches: {len(all_matches)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
