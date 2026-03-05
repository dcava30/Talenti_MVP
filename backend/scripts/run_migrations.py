import sys
from pathlib import Path


def main() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    from app.core.migrations import run_startup_migrations

    run_startup_migrations()


if __name__ == "__main__":
    main()
