from __future__ import annotations

import argparse
import json
import re
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

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_PROXY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "to",
    "was",
    "were",
    "with",
}


def _issue(dataset: Path, line_number: int, code: str, detail: str) -> dict[str, Any]:
    return {
        "dataset": str(dataset),
        "line": line_number,
        "code": code,
        "detail": detail,
    }


def _normalize_string_list(value: Any, field_name: str) -> tuple[list[str], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    if value is None:
        return [], issues
    if isinstance(value, str):
        return [value], issues
    if isinstance(value, list):
        normalized: list[str] = []
        for index, item in enumerate(value):
            if isinstance(item, str):
                if item.strip():
                    normalized.append(item)
                continue
            issues.append(
                {
                    "code": "invalid_field_item_type",
                    "detail": f"{field_name}[{index}] expected string",
                }
            )
        return normalized, issues
    issues.append(
        {
            "code": "invalid_field_type",
            "detail": f"{field_name} expected string or list of strings",
        }
    )
    return [], issues


def _validate_row(dataset: Path, line_number: int, sample: dict[str, Any]) -> tuple[bool, dict[str, Any], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    normalized = dict(sample)

    query = sample.get("query")
    if not isinstance(query, str) or not query.strip():
        issues.append(_issue(dataset, line_number, "missing_query", "query must be a non-empty string"))

    for field in [
        "expected_sources",
        "excluded_sources",
        "relevant_chunk_ids",
        "expected_tabular_terms",
        "expected_answer_terms",
        "expected_answer_contains",
    ]:
        normalized_values, field_issues = _normalize_string_list(sample.get(field), field)
        normalized[field] = normalized_values
        for field_issue in field_issues:
            issues.append(_issue(dataset, line_number, field_issue["code"], field_issue["detail"]))

    expected_confidence = sample.get("expected_confidence")
    if expected_confidence is not None:
        if not isinstance(expected_confidence, str):
            issues.append(
                _issue(
                    dataset,
                    line_number,
                    "invalid_field_type",
                    "expected_confidence expected string",
                )
            )
            normalized["expected_confidence"] = ""
        else:
            normalized["expected_confidence"] = expected_confidence

    expected_tabular_outcome = sample.get("expected_tabular_outcome")
    if expected_tabular_outcome is not None:
        if not isinstance(expected_tabular_outcome, str):
            issues.append(
                _issue(
                    dataset,
                    line_number,
                    "invalid_field_type",
                    "expected_tabular_outcome expected string",
                )
            )
            normalized["expected_tabular_outcome"] = ""
        else:
            normalized["expected_tabular_outcome"] = expected_tabular_outcome

    tabular_intent_value = sample.get("is_tabular_intent")
    if tabular_intent_value is None:
        normalized["is_tabular_intent"] = False
    elif isinstance(tabular_intent_value, bool):
        normalized["is_tabular_intent"] = tabular_intent_value
    elif isinstance(tabular_intent_value, str):
        lowered = tabular_intent_value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            normalized["is_tabular_intent"] = True
        elif lowered in {"false", "0", "no", "n"}:
            normalized["is_tabular_intent"] = False
        else:
            issues.append(
                _issue(
                    dataset,
                    line_number,
                    "invalid_field_type",
                    "is_tabular_intent expected boolean-compatible value",
                )
            )
            normalized["is_tabular_intent"] = False
    else:
        issues.append(
            _issue(
                dataset,
                line_number,
                "invalid_field_type",
                "is_tabular_intent expected boolean-compatible value",
            )
        )
        normalized["is_tabular_intent"] = False

    is_valid = not any(issue["code"] == "missing_query" for issue in issues)
    return is_valid, normalized, issues


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    total_nonempty_lines = 0

    if not path.exists():
        issues.append(_issue(path, 0, "missing_dataset", "dataset path does not exist"))
        return rows, {
            "dataset": str(path),
            "total_nonempty_lines": total_nonempty_lines,
            "valid_rows": 0,
            "invalid_rows": 0,
            "parse_errors": 0,
            "issues": issues,
        }

    invalid_rows = 0
    parse_errors = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        total_nonempty_lines += 1
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as error:
            parse_errors += 1
            invalid_rows += 1
            issues.append(
                _issue(
                    path,
                    line_number,
                    "invalid_json",
                    f"JSON decode error: {error.msg}",
                )
            )
            continue

        if not isinstance(parsed, dict):
            invalid_rows += 1
            issues.append(_issue(path, line_number, "invalid_row_shape", "row must be a JSON object"))
            continue

        is_valid, normalized, row_issues = _validate_row(path, line_number, parsed)
        issues.extend(row_issues)
        if not is_valid:
            invalid_rows += 1
            continue
        rows.append(normalized)

    summary = {
        "dataset": str(path),
        "total_nonempty_lines": total_nonempty_lines,
        "valid_rows": len(rows),
        "invalid_rows": invalid_rows,
        "parse_errors": parse_errors,
        "issues": issues,
    }
    return rows, summary


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


def _normalized_terms(text: str) -> set[str]:
    return {
        match.group(0).lower()
        for match in _TOKEN_RE.finditer(text)
        if len(match.group(0)) >= 3 and match.group(0).lower() not in _PROXY_STOPWORDS
    }


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


def _faithfulness_proxy(answer: str, context_chunks: list[dict[str, Any]]) -> tuple[bool, float]:
    normalized_answer = answer.strip().lower()
    if not normalized_answer:
        return False, 0.0

    # Abstentions are measured by abstention-specific metrics, not lexical faithfulness.
    if "cannot" in normalized_answer or "abstain" in normalized_answer:
        return False, 0.0

    answer_terms = _normalized_terms(answer)
    if not answer_terms:
        return False, 0.0

    context_terms: set[str] = set()
    for chunk in context_chunks:
        context_terms.update(_normalized_terms(str(chunk.get("text", ""))))
    if not context_terms:
        return False, 0.0

    supported_terms = answer_terms & context_terms
    return True, _safe_div(len(supported_terms), len(answer_terms))


def _correctness_proxy(sample: dict[str, Any], answer: str) -> tuple[bool, float]:
    expected_terms = {
        str(value).strip().lower()
        for value in (sample.get("expected_answer_terms") or [])
        if str(value).strip()
    }

    raw_contains = sample.get("expected_answer_contains") or []
    if isinstance(raw_contains, str):
        expected_contains = [raw_contains]
    else:
        expected_contains = [str(value) for value in raw_contains]
    expected_phrases = [value.strip().lower() for value in expected_contains if value.strip()]

    total_expectations = len(expected_terms) + len(expected_phrases)
    if total_expectations == 0:
        return False, 0.0

    answer_terms = _normalized_terms(answer)
    normalized_answer = answer.strip().lower()

    matched_terms = sum(1 for term in expected_terms if term in answer_terms)
    matched_phrases = sum(1 for phrase in expected_phrases if phrase in normalized_answer)
    matched_total = matched_terms + matched_phrases
    return True, _safe_div(matched_total, total_expectations)


def _write_markdown_report(
    path: Path,
    metrics: dict[str, float],
    sample_count: int,
    dataset_sanity: dict[str, Any],
) -> None:
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

    lines.extend(
        [
            "",
            "## Dataset Sanity",
            "",
            f"- datasets checked: {dataset_sanity['datasets_checked']}",
            f"- total non-empty rows: {dataset_sanity['total_nonempty_rows']}",
            f"- valid rows: {dataset_sanity['valid_rows']}",
            f"- invalid rows: {dataset_sanity['invalid_rows']}",
            f"- parse errors: {dataset_sanity['parse_errors']}",
        ]
    )

    issue_preview = dataset_sanity.get("issue_preview", [])
    if issue_preview:
        lines.extend(["", "### Malformed Row Preview", "", "| Dataset | Line | Code | Detail |", "|---|---:|---|---|"])
        for issue in issue_preview:
            lines.append(
                f"| {issue['dataset']} | {issue['line']} | {issue['code']} | {issue['detail']} |"
            )

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
    dataset_summaries: list[dict[str, Any]] = []
    for dataset_path in datasets:
        dataset_rows, summary = _read_jsonl(dataset_path)
        rows.extend(dataset_rows)
        dataset_summaries.append(summary)

    all_issues: list[dict[str, Any]] = []
    total_nonempty_rows = 0
    total_invalid_rows = 0
    total_parse_errors = 0
    for summary in dataset_summaries:
        total_nonempty_rows += int(summary.get("total_nonempty_lines", 0))
        total_invalid_rows += int(summary.get("invalid_rows", 0))
        total_parse_errors += int(summary.get("parse_errors", 0))
        all_issues.extend(summary.get("issues", []))

    dataset_sanity = {
        "datasets_checked": len(datasets),
        "total_nonempty_rows": total_nonempty_rows,
        "valid_rows": len(rows),
        "invalid_rows": total_invalid_rows,
        "parse_errors": total_parse_errors,
        "issues": all_issues,
        "issue_preview": all_issues[:20],
        "per_dataset": [
            {
                "dataset": summary.get("dataset"),
                "total_nonempty_lines": summary.get("total_nonempty_lines", 0),
                "valid_rows": summary.get("valid_rows", 0),
                "invalid_rows": summary.get("invalid_rows", 0),
                "parse_errors": summary.get("parse_errors", 0),
            }
            for summary in dataset_summaries
        ],
    }

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
    faithfulness_expected = 0
    faithfulness_total = 0.0
    correctness_expected = 0
    correctness_total = 0.0

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

        has_faithfulness_proxy, faithfulness_score = _faithfulness_proxy(answer, answer_context)
        if has_faithfulness_proxy:
            faithfulness_expected += 1
            faithfulness_total += faithfulness_score

        has_correctness_proxy, correctness_score = _correctness_proxy(sample, answer)
        if has_correctness_proxy:
            correctness_expected += 1
            correctness_total += correctness_score

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
        "faithfulness_proxy": _safe_div(faithfulness_total, max(1, faithfulness_expected)),
        "correctness_proxy": _safe_div(correctness_total, max(1, correctness_expected)),
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
        "dataset_sanity": dataset_sanity,
        "config": {
            "top_k": config.top_k,
            "min_retrieval_score": config.min_retrieval_score,
            "generation_mode": config.generation_mode,
            "data_path": config.data_path,
        },
    }
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _write_markdown_report(md_path, metrics, sample_count, dataset_sanity)

    print(f"Evaluated {sample_count} samples across {len(datasets)} dataset(s).")
    print(
        "Dataset sanity: "
        f"{dataset_sanity['valid_rows']} valid / {dataset_sanity['total_nonempty_rows']} non-empty rows, "
        f"{dataset_sanity['invalid_rows']} invalid, {dataset_sanity['parse_errors']} parse errors."
    )
    if dataset_sanity["issue_preview"]:
        print("Malformed row preview:")
        for issue in dataset_sanity["issue_preview"][:5]:
            print(
                f"- {issue['dataset']}:{issue['line']} [{issue['code']}] {issue['detail']}"
            )
    print(f"Wrote report JSON: {json_path}")
    print(f"Wrote report Markdown: {md_path}")


if __name__ == "__main__":
    main()
