# **SCARAG Evaluation Blueprint**

## **Purpose**

This document describes the evaluation philosophy for SCARAG.

SCARAG uses evaluation to diagnose framework behavior, not merely to produce a single quality score. The framework is designed for document-grounded retrieval systems where provenance, lifecycle, freshness, confidence, tabular grounding, and answer faithfulness matter.

The evaluation strategy should therefore answer a practical question:

**Where did the system succeed or fail, and why?**

## **Evaluation Position**

SCARAG supports an offline-first evaluation approach.

This is intentional.

Early framework evaluation should not require a live LLM provider. Teams need a way to validate ingestion, chunking, retrieval, provenance, lifecycle filtering, freshness handling, tabular grounding, and abstention behavior before connecting a production model.

Offline evaluation is not the final stage of maturity. It is the baseline.

A mature implementation may add:

* human-reviewed answer evaluation;  
* LLM-judged faithfulness checks;  
* RAGAS-style reference evaluation;  
* production telemetry;  
* user feedback loops;  
* regression suites for known failure cases.

However, those additions should complement the framework-level checks. They should not replace them.

## **Reference Versus Core**

RAGAS-style evaluation may be included as a reference evaluation path.

It should not be treated as a core SCARAG dependency.

SCARAG’s core concern extends beyond any single evaluation library. The framework must evaluate whether the system preserves evidence structure, retrieves appropriate source units, exposes provenance, respects lifecycle policy, handles tabular data safely, and abstains when evidence is insufficient.

RAGAS-style metrics can be useful for evaluating dimensions such as faithfulness, answer relevance, context precision, and context recall. Those metrics are valuable, but they sit alongside SCARAG’s framework-specific governance checks.

In short:

**RAGAS can help evaluate generated-answer behavior. SCARAG must also evaluate evidence-governance behavior.**

## **Evaluation Layers**

SCARAG evaluation should be layered.

### **Layer 1: Ingestion and Structure**

This layer checks whether source material is correctly transformed into retrievable units.

Questions to answer:

* Were supported file types ingested?  
* Were source units created correctly?  
* Were tables detected when expected?  
* Were row boundaries preserved?  
* Were headers repeated or associated correctly for tabular chunks?  
* Was boilerplate identified?  
* Were duplicate units suppressed?  
* Was extraction metadata attached?  
* Were source-unit identifiers stable across re-ingestion?

Representative checks:

* document count;  
* source-unit count;  
* chunk count;  
* duplicate fingerprint count;  
* extraction method distribution;  
* tabular versus narrative unit distribution;  
* missing metadata fields;  
* malformed source-unit IDs;  
* table-detection accuracy samples.

### **Layer 2: Metadata and Provenance**

This layer checks whether evidence remains traceable from ingestion through retrieval and answer presentation.

Questions to answer:

* Does every retrieved chunk carry source metadata?  
* Does every answer expose citation information?  
* Are citations deduplicated without hiding necessary evidence?  
* Are collapsed citations still available on demand?  
* Can a user or evaluator trace the answer back to source material?  
* Are the provenance fields sufficient for implementation needs?

Representative metrics:

* provenance completeness;  
* citation coverage;  
* missing source path rate;  
* missing extraction metadata rate;  
* missing lifecycle metadata rate;  
* citation deduplication behavior;  
* collapsed citation count.

### **Layer 3: Retrieval Quality**

This layer checks whether the retrieval system finds appropriate evidence.

Questions to answer:

* Does the expected source appear in the top-k results?  
* How early does the first relevant result appear?  
* Are the retrieved chunks actually relevant?  
* Does query expansion improve or degrade retrieval?  
* Does metadata weighting improve or distort ranking?  
* Does reranking improve final context quality?  
* Are score thresholds excluding useful evidence or allowing noise?

Representative metrics:

* hit rate at k;  
* mean reciprocal rank at k;  
* context precision at k;  
* relevant source recall;  
* retrieval score distribution;  
* threshold failure cases;  
* reranking delta;  
* query expansion delta.

### **Layer 4: Lifecycle and Freshness**

This layer checks whether retrieval respects document state.

Questions to answer:

* Are retired documents excluded when they should be?  
* Are stale documents excluded when freshness filtering is enabled?  
* Are active documents retained?  
* Are pending-review documents handled in accordance with domain policy?  
* Are soft-deleted units excluded?  
* Does re-ingestion preserve the original ingestion time and correctly update the last-upsert time?  
* Are unchanged units skipped when configured?

Representative metrics:

* lifecycle status compliance;  
* freshness compliance;  
* soft-delete exclusion compliance;  
* missing timestamp rate;  
* invalid timestamp rate;  
* stale-source retrieval rate;  
* retired-source retrieval rate;  
* re-ingestion audit consistency.

### **Layer 5: Confidence Behavior**

This layer checks whether the confidence assessment behaves as intended.

Questions to answer:

* Are base extraction tiers applied correctly?  
* Are domain confidence overlays loaded?  
* Does confidence change appropriately by extraction method?  
* Does temporal decay work when enabled?  
* Do intent-based boosts behave as expected?  
* Are low-confidence results filtered or demoted when required?  
* Are confidence thresholds too strict or too permissive?

Representative checks:

* confidence tier distribution;  
* confidence override application;  
* extraction-method-to-confidence mapping;  
* domain overlay coverage;  
* low-confidence retrieval rate;  
* confidence threshold pass/fail rate;  
* confidence debug traces.

### **Layer 6: Tabular Grounding**

This layer checks whether table-like queries are answered by row-faithful evidence.

Questions to answer:

* Does the system detect tabular intent?  
* Does it retrieve tabular chunks for table-like questions?  
* Are headers available with row evidence?  
* Does the answer use matched rows rather than nearby narrative context?  
* Does the system abstain when no row-level match exists?  
* Does schema-style fallback remain appropriately limited?  
* Are wide or sparse spreadsheets handled safely?

Representative metrics:

* tabular intent detection accuracy;  
* tabular evidence retrieval rate;  
* matched-row evidence rate;  
* tabular grounding compliance;  
* unsupported tabular answer rate;  
* row-header preservation rate;  
* schema fallback rate;  
* tabular abstention rate.

### **Layer 7: Answer Grounding**

This layer checks whether answers stay within the retrieved evidence.

Questions to answer:

* Does the answer reflect the retrieved context?  
* Does the answer add unsupported claims?  
* Does the answer omit important evidence?  
* Does it overgeneralize from a narrow source?  
* Does it distinguish evidence from inference?  
* Does it abstain when evidence is insufficient?  
* Does it cite the evidence it uses?

Representative metrics:

* faithfulness proxy;  
* answer correctness proxy;  
* citation support rate;  
* unsupported claim rate;  
* abstention correctness;  
* answer-source alignment;  
* contradiction rate.

In offline mode, lexical proxies may be used for fast iteration. These are useful but limited. They should be treated as development signals, not final semantic judgments.

### **Layer 8: Generated-Answer Quality**

This layer applies when a live or judged generation path is available.

Questions to answer:

* Is the answer relevant to the user's query?  
* Is it faithful to the retrieved evidence?  
* Is it complete enough for the intended use?  
* Is it concise enough for the interface?  
* Does it preserve uncertainty?  
* Does it avoid unsupported synthesis?  
* Does it format evidence in a usable way?

Possible evaluation methods:

* human review;  
* SME review;  
* LLM-as-judge review;  
* RAGAS-style reference evaluation;  
* golden-answer comparison;  
* rubric-based scoring.

Representative metrics:

* answer relevance;  
* faithfulness;  
* context precision;  
* context recall;  
* answer correctness;  
* answer completeness;  
* answer concision;  
* unsupported claim rate.

## **Dataset Types**

SCARAG implementations should maintain multiple types of evaluation datasets.

### **Canonical Dataset**

The canonical dataset contains representative questions that define expected system behavior.

Use this dataset to answer:

* Does the system work for the main use case?  
* Are expected sources retrievable?  
* Are expected answer patterns supported?  
* Do provenance and lifecycle checks pass?

Canonical examples should be stable and reviewed.

### **Regression Dataset**

The regression dataset contains known past failures.

Use this dataset to answer:

* Did a previous bug return?  
* Did a retrieval change break a fixed behavior?  
* Did query expansion introduce drift?  
* Did tabular grounding regress?  
* Did lifecycle filtering change unexpectedly?

Regression examples should grow over time.

### **Drift Dataset**

The drift dataset contains examples that monitor changing or fragile behavior.

Use this dataset to answer:

* Is system quality changing as the corpus changes?  
* Are new documents affecting retrieval?  
* Are synonyms or taxonomies becoming stale?  
* Are freshness rules still appropriate?  
* Are new document types introducing unexpected behavior?

Drift examples may require more frequent review.

### **Adversarial or Boundary Dataset**

The adversarial dataset contains questions the system should not answer freely.

Use this dataset to answer:

* Does the system abstain when evidence is insufficient?  
* Does it avoid stale sources?  
* Does it avoid retired documents?  
* Does it avoid unsupported tabular synthesis?  
* Does it resist misleading user phrasing?  
* Does it distinguish similar but different terms?

Boundary examples are especially important for governed domains.

## Reference Dataset Row Fields (Baseline)

The baseline offline evaluator now supports expectation-driven row fields:

* expected_confidence: expected confidence label (high, low, abstain)
* excluded_sources: source substrings that must not appear in retrieved evidence
* expected_tabular_terms: terms that should appear in matched row/header evidence for tabular intent

These fields complement existing query/expected_sources fields and enable framework checks for confidence alignment, lifecycle exclusion compliance, and tabular row-term matching.

## Baseline Extended Metrics

The offline evaluator now reports:

* confidence_alignment_rate
* lifecycle_exclusion_compliance
* tabular_row_term_match_rate
* tabular_answer_success_rate
* tabular_abstention_correctness
* dataset_sanity summary with malformed-row reporting (`invalid_json`, `invalid_row_shape`, `missing_query`)

## Reference UI and Developer Workflow Surfacing

Evaluation outputs should be surfaced at two levels:

### Per-response (reference UI)

* Surface evaluation output beside citations as compact status indicators.
* Keep indicators clickable so developers/reviewers can select diagnostic context.
* Keep detailed diagnostics in a collapsed advanced section under citations so answer-first UX remains uncluttered.
* Use explicit two-step disclosure for details (select indicator, then expand advanced section).
* Treat per-response eval surfaces as review aids, not primary user content.

### Aggregate (developer workflow)

* Run offline evaluation using scripts/run_eval.py for repeatable aggregate metrics.
* Use eval/reports/*.json for machine-readable regression comparisons and eval/reports/*.md for human review.
* When debugging a single answer, start from that response's clickable eval indicators, then correlate with aggregate report trends.
* Keep UI-level per-response cues and offline aggregate reports aligned so triage can move from symptom to metric to root cause.

### Repeatable test-data cleanup protocol

Use `scripts/reset_eval_workspace.py` to keep evaluation runs reproducible between iterations.

Recommended sequence:

1. Preview cleanup candidates:

```bash
python scripts/reset_eval_workspace.py --dry-run
```

2. Remove generated evaluation reports and temporary eval docs:

```bash
python scripts/reset_eval_workspace.py --confirm
```

3. Optional: also remove dataset JSONL files when rebuilding dataset seeds from scratch:

```bash
python scripts/reset_eval_workspace.py --confirm --delete-datasets
```

4. Optional: also clear default re-ingestion state when the test run requires a clean lifecycle state:

```bash
python scripts/reset_eval_workspace.py --confirm --clear-default-state
```

5. Verify a clean baseline before rerunning evaluation:

```bash
python scripts/reset_eval_workspace.py --dry-run
```

Notes:

* `--dry-run` never deletes files and should be used before destructive cleanup.
* `--delete-datasets` is for intentional dataset rebuild workflows; avoid it for normal report-only resets.
* `--test-docs-path` can be overridden when temporary evaluation corpus paths differ from the default `data/_eval_tmp`.

These metrics are in addition to hit rate, MRR, context precision, provenance completeness, abstention rate, and tabular grounding compliance.

## **Recommended Dataset Fields**

Each evaluation record should include enough information to diagnose behavior.

Recommended starter fields:

{  
  "id": "canonical-001",  
  "query": "User-facing question",  
  "profile": "corporate",  
  "ground\_truth": "Optional expected answer",  
  "expected\_sources": \["data/example-source.docx"\],  
  "relevant\_chunk\_ids": \["optional-explicit-chunk-id"\],  
  "is\_tabular\_intent": false,  
  "max\_doc\_age\_days": 365,  
  "allowed\_statuses": \["active", "pending\_review"\],  
  "expected\_behavior": "answer",  
  "notes": "Why this example exists"  
}

For tabular examples, include:

{  
  "is\_tabular\_intent": true,  
  "expected\_table\_headers": \["field\_a", "field\_b"\],  
  "expected\_row\_markers": \["row identifier or value"\],  
  "expected\_behavior": "row\_grounded\_answer"  
}

For abstention examples, include:

{  
  "expected\_behavior": "abstain",  
  "abstention\_reason": "no current active source"  
}

## **Benchmark Interpretation**

Evaluation reports should be interpreted as diagnostic artifacts.

A strong hit rate with weak answer faithfulness suggests a generation or grounding problem.

A weak hit rate with strong faithfulness to the retrieved context suggests a retrieval problem.

Strong retrieval with weak provenance suggests an evidence-presentation or metadata-propagation problem.

Strong answer quality with poor lifecycle compliance is still a serious failure because the answer may be based on inappropriate evidence.

Strong overall metrics with weak tabular grounding mean table-like answers remain unsafe.

No single metric should be treated as sufficient.

## **Suggested Minimum Evaluation Bundle**

For early implementation, SCARAG should track:

* hit rate at k;  
* mean reciprocal rank at k;  
* context precision at k;  
* provenance completeness;  
* freshness compliance;  
* lifecycle status compliance;  
* tabular grounding compliance;  
* abstention rate;  
* faithfulness proxy;  
* answer correctness proxy.

For mature implementation, add:

* human-reviewed faithfulness;  
* human-reviewed answer relevance;  
* RAGAS-style reference metrics;  
* production query sampling;  
* user feedback review;  
* failure taxonomy;  
* recurring regression review.

## **Failure Taxonomy**

Evaluation should record not only that a test failed, but what kind of failure occurred.

Suggested failure categories:

* ingestion failure;  
* extraction failure;  
* chunking failure;  
* table-detection failure;  
* metadata propagation failure;  
* synonym/query expansion failure;  
* retrieval miss;  
* retrieval noise;  
* reranking failure;  
* threshold failure;  
* lifecycle filtering failure;  
* freshness filtering failure;  
* confidence scoring failure;  
* tabular grounding failure;  
* generation hallucination;  
* unsupported synthesis;  
* citation failure;  
* evidence UX failure;  
* abstention failure;  
* expected-answer mismatch;  
* dataset issue.

This taxonomy makes evaluation actionable.

## **Evaluation Maturity Model**

### **Level 0: Smoke Test**

The system runs against a small corpus and returns cited answers.

This is useful for development only.

### **Level 1: Offline Retrieval Evaluation**

The system uses deterministic datasets to measure source retrieval, provenance, lifecycle compliance, and grounding proxies.

This is the minimum recommended baseline.

### **Level 2: Domain-Governed Evaluation**

The implementation adds SME-reviewed datasets, domain vocabulary checks, lifecycle policies, confidence overlays, and tabular examples.

This is the minimum recommended level for serious domain use.

### **Level 3: Generated-Answer Evaluation**

The implementation adds live-model answer review, human judging, RAGAS-style reference evaluation, or rubric-based LLM judging.

This is appropriate once the live generation path is connected.

### **Level 4: Production Monitoring**

The implementation samples production queries, tracks failures, captures feedback, reviews drift, and updates regression datasets.

This is appropriate for deployed systems.

## **Evaluation Principles**

SCARAG evaluation should follow these principles:

1. Evaluate retrieval before blaming generation.  
2. Evaluate provenance before trusting fluency.  
3. Evaluate lifecycle compliance before accepting relevance.  
4. Evaluate tabular questions separately from narrative questions.  
5. Treat abstention as a valid success case.  
6. Use RAGAS-style evaluation as a reference path, not a framework dependency.  
7. Prefer diagnostic visibility over aggregate scores.  
8. Keep domain experts involved in dataset design.  
9. Preserve regression examples when failures are found.  
10. Re-tune evaluation when the corpus, domain, or implementation changes.

## **Final Position**

SCARAG evaluation is not only about whether an answer sounds good.

It is about whether the system retrieved the right evidence, respected the right constraints, exposed the right provenance, and answered only within the bounds of what the evidence could support.

The goal is not merely answer quality.

The goal is accountable answer quality.

