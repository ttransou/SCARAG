function normalizeEvaluation(data) {
  const message = data?.message || {};
  const generation = message.generation;
  const provenance = message.provenance_validation;
  const tabularTrace = message.tabular_trace;

  const signals = [];
  const details = {};

  if (provenance && typeof provenance === 'object') {
    const complete = provenance.complete === true;
    signals.push({
      key: 'provenance',
      label: complete ? 'Provenance pass' : 'Provenance warn',
      status: complete ? 'pass' : 'warn',
    });

    details.provenance = {
      title: 'Provenance diagnostics',
      lines: [
        `Complete: ${complete ? 'yes' : 'no'}`,
        `Source valid: ${provenance?.source_validation?.valid ?? 0}/${provenance?.source_validation?.total ?? 0}`,
        `Citation valid: ${provenance?.citation_validation?.valid ?? 0}/${provenance?.citation_validation?.total ?? 0}`,
        `Citation quality: ${provenance?.citation_quality?.quality_rate ?? 'n/a'}`,
      ],
    };
  }

  if (generation && typeof generation === 'object') {
    const abstained = generation.abstained === true;
    signals.push({
      key: 'generation',
      label: abstained ? 'Generation abstained' : 'Generation grounded',
      status: abstained ? 'warn' : 'pass',
    });

    details.generation = {
      title: 'Generation diagnostics',
      lines: [
        `Grounding policy: ${generation.grounding_policy || 'unknown'}`,
        `Abstained: ${abstained ? 'yes' : 'no'}`,
        `Reason code: ${generation.reason_code || 'n/a'}`,
        `Used context: ${generation.used_context_count ?? 0}`,
      ],
    };
  }

  if (tabularTrace && typeof tabularTrace === 'object') {
    signals.push({
      key: 'tabular',
      label: 'Tabular trace',
      status: 'info',
    });

    details.tabular = {
      title: 'Tabular diagnostics',
      lines: [
        `Tabular intent: ${tabularTrace.tabular_intent === true ? 'yes' : 'no'}`,
        `Matched rows: ${tabularTrace.matched_row_count ?? 0}`,
        `Grounded chunks: ${tabularTrace.grounded_chunk_count ?? 0}`,
      ],
    };
  }

  return { signals, details };
}

export function normalizeAssistantResponse(data, assistantMessageId) {
  const answer = data?.answer || data?.message?.text || 'No answer returned.';
  const citations = Array.isArray(data?.citations)
    ? data.citations
    : Array.isArray(data?.sources)
      ? data.sources
      : [];
  const evaluation = normalizeEvaluation(data);

  return {
    content: answer,
    citations: citations.slice(0, 5).map((citation, index) => ({
      id: `${assistantMessageId}-${index}`,
      title: citation.title || citation.document || `Source ${index + 1}`,
      snippet: citation.snippet || citation.text || citation.content || 'Retrieved evidence will appear here.',
      link: citation.link || '#',
    })),
    confidence: data?.confidence || (citations.length ? 'High' : 'Low'),
    score: data?.score ?? null,
    evaluation,
  };
}