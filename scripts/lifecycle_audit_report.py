from __future__ import annotations

import argparse
import json
from pathlib import Path

from scarag.lifecycle import LifecycleStateStore


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate lifecycle audit summary report.")
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
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    return parser.parse_args()


def _to_markdown(report: dict[str, object], state_path: str, audit_log_path: str) -> str:
    state = report.get("state", {}) if isinstance(report, dict) else {}
    events = report.get("events", {}) if isinstance(report, dict) else {}
    timestamps = report.get("timestamps", {}) if isinstance(report, dict) else {}

    status_counts = state.get("status_counts", {}) if isinstance(state, dict) else {}
    event_counts = events.get("event_counts", {}) if isinstance(events, dict) else {}

    lines = [
        "# Lifecycle Audit Report",
        "",
        f"- state_path: {state_path}",
        f"- audit_log_path: {audit_log_path}",
        "",
        "## State Summary",
        f"- total_records: {state.get('total_records', 0)}",
        f"- active_count: {state.get('active_count', 0)}",
        f"- soft_deleted_count: {state.get('soft_deleted_count', 0)}",
        "",
        "## Status Counts",
    ]

    if isinstance(status_counts, dict) and status_counts:
        for status, count in sorted(status_counts.items()):
            lines.append(f"- {status}: {count}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Timestamp Quality",
            f"- missing_ingestion_iso_ts: {timestamps.get('missing_ingestion_iso_ts', 0)}",
            f"- invalid_ingestion_iso_ts: {timestamps.get('invalid_ingestion_iso_ts', 0)}",
            f"- missing_last_upsert_iso_ts: {timestamps.get('missing_last_upsert_iso_ts', 0)}",
            f"- invalid_last_upsert_iso_ts: {timestamps.get('invalid_last_upsert_iso_ts', 0)}",
            "",
            "## Event Counts",
            f"- total_events: {events.get('total_events', 0)}",
        ]
    )

    if isinstance(event_counts, dict) and event_counts:
        for action, count in sorted(event_counts.items()):
            lines.append(f"- {action}: {count}")
    else:
        lines.append("- none")

    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    state_path = str(Path(args.state_path))
    audit_log_path = str(Path(args.audit_log_path))
    store = LifecycleStateStore(state_path)
    report = store.build_audit_report(audit_log_path=audit_log_path)

    if args.format == "markdown":
        print(_to_markdown(report, state_path=state_path, audit_log_path=audit_log_path))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
