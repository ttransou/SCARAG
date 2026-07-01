# **SCARAG: Premise and Design Philosophy**

SCARAG begins from a practical observation: most Retrieval-Augmented Generation systems do not fail simply because the model is weak. They fail because the system does not know enough about the documents it is retrieving.

A naive RAG pipeline treats source material as text to be split, embedded, retrieved, and summarized. That approach may work for small demos, but it breaks down quickly in real implementation environments. Enterprise, legal, financial, insurance, IT, compliance, support, and operational knowledge bases are not just collections of paragraphs. They are governed artifacts. They have provenance, lifecycle state, ownership, freshness expectations, formatting constraints, tabular structures, repeated boilerplate, conflicting versions, domain-specific vocabulary, and different standards of evidentiary trust.

SCARAG is built around the belief that those signals are not secondary implementation details. They are the foundation of reliable retrieval.

The premise is simple:

**A RAG system cannot be meaningfully grounded unless it understands the structure, status, and semantics of the evidence it retrieves.**

For that reason, SCARAG is schema-centric rather than model-centric. The framework prioritizes explicit metadata, source-unit identity, document type, extraction method, lifecycle timestamps, confidence rules, domain vocabulary, tabular row fidelity, and evidence presentation. The goal is not to make the language model appear more authoritative. The goal is to make the retrieval, evidence, and answer layers accountable for the materials they use.

## **Why “Schema-Centric” Matters**

In many RAG systems, schema is treated as a convenience: useful when the source data already has clean fields, optional otherwise. SCARAG treats schema as an interpretive layer.

Schema does not only mean database columns or JSON keys. In this framework, schema refers to any explicit representation of meaning that helps the system understand what a source unit is, where it came from, how it was extracted, how current it is, whether it belongs to a table or narrative document, whether it is boilerplate, whether it is active or retired, and how strongly it should be trusted for a given user query.

That shift matters because retrieval is not only a search problem. It is also a judgment problem.

A retrieved chunk may be textually similar to a query but still be wrong for the answer. It may come from an outdated file, a retired policy, a repeated footer, an inferred table, a low-confidence extraction, or a document type that should not answer the user’s intent. Conversely, a less textually obvious chunk may be more trustworthy because its metadata, lifecycle status, or domain profile makes it the correct evidence.

SCARAG therefore treats retrieval quality as a combination of lexical relevance, semantic relevance, metadata fit, lifecycle validity, provenance completeness, and domain-specific trust.

## **Agnostic Does Not Mean Generic**

## **Agnostic Does Not Mean Generic**

SCARAG is domain-agnostic, but it is **not** domain-indifferent.

The framework can be adapted for evidence-sensitive corpora across many fields: finance, legal, insurance, IT, corporate policy, support knowledge, test results, humanities research, archival collections, museum documentation, art-historical records, literary corpora, oral histories, and cultural heritage materials.

These domains differ in purpose, but they share a common problem: the answer is only as trustworthy as the evidence layer beneath it.

In a financial implementation, that may mean freshness windows, report dates, tabular precision, and lifecycle status.

In a legal or insurance implementation, it may mean jurisdiction, effective dates, policy versions, exclusions, and conflict resolution.

In an IT or support implementation, it may mean active procedures, system names, service ownership, error codes, and retired knowledge articles.

In a humanities implementation, it may include provenance, attribution, periodization, archival context, interpretive uncertainty, translation history, catalog metadata, edition differences, authorship questions, and the distinction between primary and secondary sources, annotations, and scholarly interpretation.

**SCARAG does not assume that a single universal taxonomy, a single synonym list, a single confidence policy, or a single freshness rule can serve all of these uses.**

The framework supplies reusable primitives.

The implementation supplies domain judgment.

## **Human-Owned NLP Tailoring**

Domain adaptation is not only a technical task. It is a human linguistic task.

Real corpora contain false friends, local abbreviations, overloaded terms, policy-specific language, internal shorthand, product names, procedural references, table labels, document codes, and legacy naming conventions. A generic embedding model may capture some semantic similarity, but it will not reliably understand the operational meaning of those terms without deliberate tailoring.

SCARAG therefore assumes that subject-matter experts, analysts, knowledge managers, and NLP-aware implementers must participate in the adaptation process. The thesaurus, ontology, profile rules, tabular intent vocabulary, lifecycle states, and evaluation examples should be treated as governed artifacts.

**The human role is not incidental. It is the layer that makes the system fit for use.**

## **Grounding as a Contract**

SCARAG treats answer grounding as a contract between the system and the user.

The system should not merely produce a fluent answer. It should show what evidence was used, preserve provenance, expose confidence-relevant metadata, and abstain when evidence is missing, stale, contradictory, or structurally insufficient.

This is especially important for tabular and operational data. If a user asks about rows, values, scores, fields, metrics, or tables, the framework should not synthesize an answer from nearby narrative text. It should retrieve row-faithful evidence or decline to answer. In SCARAG, abstention is not failure. It is a correct behavior.

The framework’s evidence UX follows the same principle. Citations are not decorative. They are part of the answer contract. Dense evidence can be deduplicated, collapsed, and placed on demand, but it should remain available for inspection.

## **Evaluation Philosophy**

SCARAG’s evaluation stance is intentionally layered.

The current offline harness supports fast, repeatable checks for retrieval quality, grounding behavior, provenance completeness, lifecycle compliance, freshness compliance, tabular grounding, and abstention behavior. These metrics are not intended to be the final word on answer quality. They are intended to make iteration visible.

Offline lexical proxies are useful because they are cheap, deterministic, and available before a live LLM provider is wired into the stack. They allow teams to test whether expected sources are retrieved, whether provenance exists, whether retired or stale content is excluded, and whether tabular guardrails behave correctly.

However, lexical metrics are not enough. Mature implementations should add LLM-judged or human-judged evaluation where appropriate. RAGAS-style evaluation can be layered in to assess dimensions such as faithfulness, answer relevancy, context precision, and context recall. Those metrics are useful because they separate different failure modes: whether the retriever found the right evidence, whether the answer used that evidence, whether the answer stayed faithful to the retrieved context, and whether the response actually addressed the question.

**SCARAG’s position is that evaluation should not be a single score. It should be a diagnostic map.**

A high-level answer quality score is less useful than knowing where the system failed. Did retrieval miss the right document? Did chunking separate the answer from its context? Did the system retrieve the correct file but the wrong row? Did the answer generator overstate what the evidence supported? Did the citation layer hide essential provenance? Did the freshness policy allow an outdated document? Did synonym expansion help, or did it drift the query?

The goal of evaluation is not to make a benchmark look good. The goal is to make the system's behavior sufficiently legible to improve it.

## **Expected Goal**

The expected goal of SCARAG is to provide a reusable, inspectable, implementation-ready foundation for document-grounded question answering across domains where provenance, lifecycle, and evidence quality matter.

A successful SCARAG implementation should be able to:

1. ingest heterogeneous source material without erasing meaningful structure;  
2. preserve source-unit metadata from ingestion through answer presentation;  
3. distinguish narrative, tabular, boilerplate, and lifecycle-sensitive evidence;  
4. retrieve relevant chunks using both content similarity and metadata-aware weighting;  
5. apply domain-specific vocabulary, synonym, confidence, freshness, and lifecycle rules;  
6. answer only from retrieved evidence;  
7. expose citations and provenance in a usable evidence interface;  
8. abstain when the available evidence is insufficient;  
9. support repeatable offline evaluation before live provider integration;  
10. evolve toward RAGAS-style, LLM-judged, human-reviewed, or production-observed evaluation as implementation maturity increases.

In practical terms, SCARAG should help teams avoid rebuilding the same fragile RAG pipeline from scratch for every corpus. It should give them a framework that is configurable, auditable, and honest about its boundaries.

The framework is not trying to replace expert judgment. It is trying to encode the places where expert judgment belongs.

## **What SCARAG Is Not**

SCARAG is not a chatbot template.

It is not a claim that metadata alone solves RAG.

It is not a universal ontology.

It is not a live LLM provider wrapper.

It is not an attempt to hide complexity behind a single abstraction.

It is a framework for making the complexity explicit: source structure, extraction quality, lifecycle state, domain vocabulary, retrieval behavior, confidence assessment, evidence presentation, and evaluation.

That explicitness is the point.

The more consequential the corpus, the less acceptable it is for retrieval to be a black box. SCARAG is designed for teams that need to know not only what answer was produced, but also why it was produced, from what evidence, under which assumptions, and with what limitations.

## **Core Claim**

SCARAG argues that reliable RAG is not achieved by retrieval plus generation alone.

Reliable RAG requires governed retrieval, schema-aware evidence, domain-owned semantics, lifecycle controls, confidence-aware grounding, and evaluation capable of distinguishing retrieval failure from generation failure.

In that sense, SCARAG is less a single implementation than a design posture:

**Make the evidence legible before asking the model to speak.**

