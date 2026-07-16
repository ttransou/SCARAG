from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scarag.confidence import resolve_confidence
from scarag.config import RagConfig
from scarag.generation.answerer import generate_answer
from scarag.ingestion.loader import load_documents
from scarag.pipeline import build_chunk_index, is_tabular_intent, load_thesaurus, retrieve_chunks
from scarag.provenance import validate_provenance
from scarag.tabular_grounding import apply_tabular_grounding


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


def _to_citation(chunk: dict[str, Any], rank: int) -> dict[str, Any]:
    source = str(chunk.get("source", "unknown"))
    return {
        "id": str(chunk.get("chunk_id", f"chunk-{rank}")),
        "title": source.split("/")[-1],
        "document": source,
        "snippet": str(chunk.get("text", ""))[:280],
        "score": chunk.get("score", 0.0),
        "chunk_id": chunk.get("chunk_id"),
        "doc_type": chunk.get("doc_type", "unknown"),
    }


def _confidence_matches(sample: dict[str, Any], label: str) -> tuple[bool, bool]:
    expected = str(sample.get("expected_confidence", "")).strip().lower()
    if not expected:
        return False, False
    return True, expected == label.strip().lower()


def _excluded_sources_respected(retrieved: list[dict[str, Any]], sample: dict[str, Any]) -> tuple[bool, bool]:
    excluded_sources = [str(value).strip() for value in (sample.get("excluded_sources") or []) if str(value).strip()]
    if not excluded_sources:
        return False, False

    violated = False
    for chunk in retrieved:
        source = str(chunk.get("source", ""))
        if any(value in source for value in excluded_sources):
            violated = True
            break
    return True, not violated


def _tabular_terms_matched(
    grounded_chunks: list[dict[str, Any]],
    sample: dict[str, Any],
) -> tuple[bool, bool]:
    expected_terms = {
        str(value).strip().lower()
        for value in (sample.get("expected_tabular_terms") or [])
        if str(value).strip()
    }
    if not expected_terms:
        return False, False

    observed_terms: set[str] = set()
    for chunk in grounded_chunks:
        for term in chunk.get("matched_terms", []):
            observed_terms.add(str(term).strip().lower())
    return True, bool(expected_terms & observed_terms)


def _tabular_outcome_matches(
    sample: dict[str, Any],
    grounded_chunks: list[dict[str, Any]],
    answer: str,
) -> tuple[bool, str, bool]:
    expected = str(sample.get("expected_tabular_outcome", "")).strip().lower()
    if not expected:
        return False, "", False

    normalized_answer = answer.strip().lower()
    abstained = "cannot" in normalized_answer or "abstain" in normalized_answer
    succeeded = any(bool(chunk.get("tabular_grounded")) for chunk in grounded_chunks)

    if expected == "answer":
        return True, expected, succeeded and not abstained
    if expected == "abstain":
        return True, expected, abstained
    return False, expected, False


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
    confidence_expected = 0
    confidence_matched = 0
    lifecycle_expected = 0
    lifecycle_compliant = 0
    tabular_term_expected = 0
    tabular_term_matched = 0
    tabular_answer_expected = 0
    tabular_answer_matched = 0
    tabular_abstention_expected = 0
    tabular_abstention_matched = 0

    for sample in rows:
        query = str(sample.get("query", "")).strip()
        if not query:
            continue

        retrieved = retrieve_chunks(query, chunks, config, thesaurus)
        tabular_query = is_tabular_intent(query, thesaurus)
        grounded_chunks, _ = apply_tabular_grounding(
            query,
            retrieved,
            tabular_intent=tabular_query,
        )
        answer_context = grounded_chunks if tabular_query else retrieved
        answer = generate_answer(
            query,
            answer_context,
            mode=config.generation_mode,
            tabular_intent=tabular_query,
        )
        confidence = resolve_confidence(
            query,
            answer_context,
            tabular_intent=tabular_query,
            thesaurus=thesaurus,
            temporal_decay_enabled=config.confidence_temporal_decay_enabled,
            temporal_decay_half_life_days=config.confidence_temporal_decay_half_life_days,
            temporal_decay_floor=config.confidence_temporal_decay_floor,
            intent_adjustment_enabled=config.confidence_intent_adjustment_enabled,
            intent_match_boost=config.confidence_intent_match_boost,
            intent_mismatch_penalty=config.confidence_intent_mismatch_penalty,
            intent_adjustment_floor=config.confidence_intent_adjustment_floor,
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

        eval_citations = [_to_citation(chunk, index) for index, chunk in enumerate(answer_context)]
        provenance_report = validate_provenance(answer_context, eval_citations)
        if provenance_report["complete"]:
            provenance_complete += 1

        if confidence.label == "abstain" or "cannot" in answer.lower() or "abstain" in answer.lower():
            abstentions += 1

        has_conf_expectation, conf_match = _confidence_matches(sample, confidence.label)
        if has_conf_expectation:
            confidence_expected += 1
            if conf_match:
                confidence_matched += 1

        has_lifecycle_expectation, lifecycle_ok = _excluded_sources_respected(retrieved, sample)
        if has_lifecycle_expectation:
            lifecycle_expected += 1
            if lifecycle_ok:
                lifecycle_compliant += 1

        sample_tabular = bool(sample.get("is_tabular_intent"))
        if sample_tabular:
            tabular_samples += 1
            has_tabular = any(bool(chunk.get("tabular_grounded")) for chunk in answer_context)
            abstained = "cannot" in answer.lower() or "abstain" in answer.lower()
            if has_tabular or abstained:
                tabular_compliant += 1

        has_tabular_term_expectation, tabular_term_ok = _tabular_terms_matched(grounded_chunks, sample)
        if has_tabular_term_expectation:
            tabular_term_expected += 1
            if tabular_term_ok:
                tabular_term_matched += 1

        has_tabular_outcome, expected_tabular_outcome, tabular_outcome_ok = _tabular_outcome_matches(
            sample,
            grounded_chunks,
            answer,
        )
        if has_tabular_outcome:
            if expected_tabular_outcome == "answer":
                tabular_answer_expected += 1
                if tabular_outcome_ok:
                    tabular_answer_matched += 1
            elif expected_tabular_outcome == "abstain":
                tabular_abstention_expected += 1
                if tabular_outcome_ok:
                    tabular_abstention_matched += 1

    sample_count = len(rows)
    metrics = {
        "hit_rate_at_k": _safe_div(hit_count, sample_count),
        "mrr_at_k": _safe_div(reciprocal_rank_total, sample_count),
        "context_precision_at_k": _safe_div(context_precision_total, sample_count),
        "provenance_completeness": _safe_div(provenance_complete, sample_count),
        "abstention_rate": _safe_div(abstentions, sample_count),
        "tabular_grounding_compliance": _safe_div(tabular_compliant, max(1, tabular_samples)),
        "confidence_alignment_rate": _safe_div(confidence_matched, max(1, confidence_expected)),
        "lifecycle_exclusion_compliance": _safe_div(lifecycle_compliant, max(1, lifecycle_expected)),
        "tabular_row_term_match_rate": _safe_div(tabular_term_matched, max(1, tabular_term_expected)),
        "tabular_answer_success_rate": _safe_div(tabular_answer_matched, max(1, tabular_answer_expected)),
        "tabular_abstention_correctness": _safe_div(
            tabular_abstention_matched,
            max(1, tabular_abstention_expected),
        ),
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
