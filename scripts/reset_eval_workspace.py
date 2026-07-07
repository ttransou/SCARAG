from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _remove_path(path: Path, dry_run: bool) -> bool:
    if not path.exists():
        return False
    if dry_run:
        print(f"[dry-run] would remove {path}")
        return True
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    print(f"removed {path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset generated SCARAG evaluation artifacts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--delete-datasets", action="store_true")
    parser.add_argument("--test-docs-path", default="data/_eval_tmp")
    parser.add_argument("--clear-default-state", action="store_true")
    args = parser.parse_args()

    targets: list[Path] = []
    reports_dir = Path("eval/reports")
    if reports_dir.exists():
        targets.extend(path for path in reports_dir.glob("offline_eval_*"))

    if args.delete_datasets:
        datasets_dir = Path("eval/datasets")
        if datasets_dir.exists():
            targets.extend(path for path in datasets_dir.glob("*.jsonl"))

    eval_tmp = Path(args.test_docs_path)
    if eval_tmp.exists():
        targets.append(eval_tmp)

    if args.clear_default_state:
        state_file = Path(".rag_state/reingestion.json")
        if state_file.exists():
            targets.append(state_file)

    if not targets:
        print("No generated evaluation artifacts found.")
        return

    if not args.confirm and not args.dry_run:
        print("Refusing to delete files without --confirm. Use --dry-run to preview.")
        return

    removed = 0
    for target in targets:
        if _remove_path(target, args.dry_run):
            removed += 1

    if args.dry_run:
        print(f"Dry run complete. {removed} path(s) would be removed.")
    else:
        print(f"Reset complete. Removed {removed} path(s).")


if __name__ == "__main__":
    main()
