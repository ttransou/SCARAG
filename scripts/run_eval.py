from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scarag.config import RagConfig
from scarag.generation.answerer import generate_answer
from scarag.ingestion.loader import load_documents
from scarag.pipeline import build_chunk_index, is_tabular_intent, load_thesaurus, retrieve_chunks


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _is_relevant(chunk: dict[str, Any], sample: dict[str, Any]) -> bool:
    expected_sources = sample.get("expected_sources") or []
    relevant_chunk_ids = sample.get("relevant_chunk_ids") or sample.get("relevant_chunk)ids") or []
    source = str(chunk.get("source", ""))
    chunk_id = str(chunk.get("chunk_id", ""))

    if expected_sources and any(str(value) in source for value in expected_sources):
        return True
    if relevant_chunk_ids and chunk_id in {str(value) for value in relevant_chunk_ids}:
        return True
    return False


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _write_markdown_report(path: Path, metrics: dict[str, float], sample_count: int) -> None:
    lines = [
        "# SCARAG Offline Evaluation",
        "",
        f"Samples evaluated: {sample_count}",
        "",
        "## Metric Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in metrics.items():
        lines.append(f"| {key} | {value:.4f} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline SCARAG evaluation against JSONL datasets")
    parser.add_argument("--data", default="data")
    parser.add_argument("--dataset", action="append", default=[])
    parser.add_argument("--generation-mode", default="extractive")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--thesaurus", default="config/synonyms.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-retrieval-score", type=float, default=0.25)
    args = parser.parse_args()

    config = RagConfig.from_profile(
        args.profile,
        data_path=args.data,
        generation_mode=args.generation_mode,
        top_k=args.top_k,
        min_retrieval_score=args.min_retrieval_score,
        thesaurus_path=args.thesaurus,
    )

    documents = load_documents(config.data_path)
    chunks = build_chunk_index(documents, config)
    thesaurus = load_thesaurus(config)

    datasets = [Path(path) for path in args.dataset]
    rows: list[dict[str, Any]] = []
    for dataset_path in datasets:
        rows.extend(_read_jsonl(dataset_path))

    if not rows:
        print("No evaluation rows found. Provide --dataset JSONL files.")
        return

    hit_count = 0
    reciprocal_rank_total = 0.0
    context_precision_total = 0.0
    provenance_complete = 0
    abstentions = 0
    tabular_compliant = 0
    tabular_samples = 0

    for sample in rows:
        query = str(sample.get("query", "")).strip()
        if not query:
            continue

        retrieved = retrieve_chunks(query, chunks, config, thesaurus)
        answer = generate_answer(
            query,
            retrieved,
            mode=config.generation_mode,
            tabular_intent=is_tabular_intent(query, thesaurus),
        )

        relevant_positions: list[int] = []
        for index, chunk in enumerate(retrieved, start=1):
            if _is_relevant(chunk, sample):
                relevant_positions.append(index)

        if relevant_positions:
            hit_count += 1
            reciprocal_rank_total += 1.0 / min(relevant_positions)

        relevant_retrieved = len(relevant_positions)
        context_precision_total += _safe_div(relevant_retrieved, max(1, len(retrieved)))

        if all(chunk.get("source") and chunk.get("chunk_id") for chunk in retrieved):
            provenance_complete += 1

        if "cannot" in answer.lower() or "abstain" in answer.lower():
            abstentions += 1

        sample_tabular = bool(sample.get("is_tabular_intent"))
        if sample_tabular:
            tabular_samples += 1
            has_tabular = any(bool(chunk.get("is_tabular")) for chunk in retrieved)
            abstained = "cannot" in answer.lower() or "abstain" in answer.lower()
            if has_tabular or abstained:
                tabular_compliant += 1

    sample_count = len(rows)
    metrics = {
        "hit_rate_at_k": _safe_div(hit_count, sample_count),
        "mrr_at_k": _safe_div(reciprocal_rank_total, sample_count),
        "context_precision_at_k": _safe_div(context_precision_total, sample_count),
        "provenance_completeness": _safe_div(provenance_complete, sample_count),
        "abstention_rate": _safe_div(abstentions, sample_count),
        "tabular_grounding_compliance": _safe_div(tabular_compliant, max(1, tabular_samples)),
    }

    reports_dir = Path("eval/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = reports_dir / f"offline_eval_{stamp}.json"
    md_path = reports_dir / f"offline_eval_{stamp}.md"

    report = {
        "timestamp": stamp,
        "datasets": [str(path) for path in datasets],
        "sample_count": sample_count,
        "metrics": metrics,
        "config": {
            "top_k": config.top_k,
            "min_retrieval_score": config.min_retrieval_score,
            "generation_mode": config.generation_mode,
            "data_path": config.data_path,
        },
    }
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _write_markdown_report(md_path, metrics, sample_count)

    print(f"Evaluated {sample_count} samples across {len(datasets)} dataset(s).")
    print(f"Wrote report JSON: {json_path}")
    print(f"Wrote report Markdown: {md_path}")


if __name__ == "__main__":
    main()
