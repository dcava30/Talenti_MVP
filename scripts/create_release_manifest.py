from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Talenti release manifest.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--acs-worker-image", required=True)
    parser.add_argument("--model1-image", required=True)
    parser.add_argument("--model2-image", required=True)
    parser.add_argument("--frontend-source-sha", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = {
        "version": args.version,
        "git_sha": args.git_sha,
        "backend_image": args.backend_image,
        "acs_worker_image": args.acs_worker_image,
        "model1_image": args.model1_image,
        "model2_image": args.model2_image,
        "frontend_source_sha": args.frontend_source_sha,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
