from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Placeholder deduplication script")
    parser.add_argument("--data", default="data")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--output")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print("No data directory found.")
        return

    files = sorted(path for path in data_path.rglob("*") if path.is_file())
    print(f"Discovered {len(files)} files; dedupe logic is a placeholder for now.")
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text("{}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
