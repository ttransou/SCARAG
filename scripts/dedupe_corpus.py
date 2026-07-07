from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _fingerprint(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _iter_files(data_path: Path) -> list[Path]:
    return sorted(path for path in data_path.rglob("*") if path.is_file())


def _analyze(data_path: Path) -> dict[str, Any]:
    files = _iter_files(data_path)
    fingerprints: dict[str, list[str]] = {}
    line_fingerprints: dict[str, int] = {}

    for file_path in files:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        normalized = _normalize_text(content)
        if normalized:
            file_fp = _fingerprint(normalized)
            fingerprints.setdefault(file_fp, []).append(str(file_path))

        for line in content.splitlines():
            cleaned = _normalize_text(line)
            if len(cleaned.split()) < 4:
                continue
            line_fp = _fingerprint(cleaned)
            line_fingerprints[line_fp] = line_fingerprints.get(line_fp, 0) + 1

    duplicates = [
        {
            "fingerprint": fp,
            "occurrences": len(paths),
            "sources": paths,
        }
        for fp, paths in fingerprints.items()
        if len(paths) > 1
    ]
    duplicates.sort(key=lambda item: item["occurrences"], reverse=True)

    repeated_boilerplate = [
        {
            "fingerprint": fp,
            "occurrences": count,
        }
        for fp, count in line_fingerprints.items()
        if count > 2
    ]
    repeated_boilerplate.sort(key=lambda item: item["occurrences"], reverse=True)

    return {
        "file_count": len(files),
        "unique_content_fingerprints": len(fingerprints),
        "duplicate_groups": duplicates,
        "repeated_boilerplate": repeated_boilerplate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect duplicate content and repeated boilerplate in corpus")
    parser.add_argument("--data", default="data")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--output")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print("No data directory found.")
        return

    report = _analyze(data_path)
    duplicate_groups = report["duplicate_groups"][: args.top]
    repeated_boilerplate = report["repeated_boilerplate"][: args.top]

    print(f"Discovered {report['file_count']} files in {data_path}.")
    print(f"Unique content fingerprints: {report['unique_content_fingerprints']}")
    print(f"Duplicate groups: {len(report['duplicate_groups'])}")
    if duplicate_groups:
        print("Top duplicate groups:")
        for group in duplicate_groups:
            print(f"- {group['occurrences']} files share fingerprint {group['fingerprint']}")

    print(f"Repeated boilerplate lines: {len(report['repeated_boilerplate'])}")
    if repeated_boilerplate:
        print("Top repeated boilerplate fingerprints:")
        for item in repeated_boilerplate:
            print(f"- {item['occurrences']} repeated lines for fingerprint {item['fingerprint']}")

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote JSON report: {args.output}")


if __name__ == "__main__":
    main()
