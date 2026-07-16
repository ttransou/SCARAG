export function normalizeAssistantResponse(data, assistantMessageId) {
  const answer = data?.answer || data?.message?.text || 'No answer returned.';
  const citations = Array.isArray(data?.citations)
    ? data.citations
    : Array.isArray(data?.sources)
      ? data.sources
      : [];

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
  };
}