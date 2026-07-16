from __future__ import annotations

import argparse
import json
from pathlib import Path

from scarag.lifecycle import LifecycleStateStore


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Permanently purge soft-deleted lifecycle records from state."
    )
    parser.add_argument(
        "--state-path",
        default="data/.scarag_lifecycle_state.json",
        help="Path to lifecycle state JSON file.",
    )
    parser.add_argument(
        "--audit-log-path",
        default="data/.scarag_lifecycle_audit.jsonl",
        help="Path to lifecycle audit JSONL log.",
    )
    parser.add_argument(
        "--older-than-days",
        type=int,
        default=None,
        help="Only purge records soft-deleted at least this many days ago.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview purge impact without writing changes.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    state_path = str(Path(args.state_path))
    audit_log_path = str(Path(args.audit_log_path))

    store = LifecycleStateStore(
        state_path,
        audit_log_path=audit_log_path,
        audit_logging_enabled=True,
    )
    result = store.hard_purge_soft_deleted(
        older_than_days=args.older_than_days,
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
