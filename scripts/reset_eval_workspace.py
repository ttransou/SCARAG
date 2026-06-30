from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Placeholder evaluation workspace reset script")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--delete-datasets", action="store_true")
    parser.add_argument("--test-docs-path", default="data/_eval_tmp")
    parser.add_argument("--clear-default-state", action="store_true")
    args = parser.parse_args()

    print("Evaluation workspace reset placeholder executed.")
    if args.dry_run:
        print("Dry run only; no changes made.")


if __name__ == "__main__":
    main()
