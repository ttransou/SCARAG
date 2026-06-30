from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Placeholder evaluation harness")
    parser.add_argument("--data", default="data")
    parser.add_argument("--dataset", action="append", default=[])
    parser.add_argument("--generation-mode", default="extractive")
    args = parser.parse_args()

    print(f"Offline evaluation placeholder for {args.generation_mode} mode")
    print(f"Datasets requested: {args.dataset or ['(none)']}")
    Path("eval/reports").mkdir(parents=True, exist_ok=True)
    Path("eval/reports/.gitkeep").write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
