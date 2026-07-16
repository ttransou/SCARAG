import test from 'node:test';
import assert from 'node:assert/strict';

import { normalizeAssistantResponse } from './responseNormalization.js';

test('normalizeAssistantResponse prefers modern citations payload', () => {
  const normalized = normalizeAssistantResponse(
    {
      answer: 'Grounded answer',
      message: {
        generation: {
          grounding_policy: 'extractive',
          abstained: false,
          reason_code: null,
          used_context_count: 2,
        },
        provenance_validation: {
          complete: true,
          source_validation: { valid: 2, total: 2 },
          citation_validation: { valid: 1, total: 1 },
          citation_quality: { quality_rate: 1.0 },
        },
      },
      citations: [
        {
          title: 'Policy',
          snippet: 'Policy alpha beta',
          link: '/docs/policy',
        },
      ],
      confidence: 'high',
      score: 0.91,
      sources: [
        {
          title: 'Legacy source should not be used',
          snippet: 'legacy',
        },
      ],
    },
    42,
  );

  assert.equal(normalized.content, 'Grounded answer');
  assert.equal(normalized.confidence, 'high');
  assert.equal(normalized.score, 0.91);
  assert.deepEqual(normalized.evaluation.signals, [
    { key: 'provenance', label: 'Provenance pass', status: 'pass' },
    { key: 'generation', label: 'Generation grounded', status: 'pass' },
  ]);
  assert.deepEqual(normalized.citations, [
    {
      id: '42-0',
      title: 'Policy',
      snippet: 'Policy alpha beta',
      link: '/docs/policy',
    },
  ]);
});

test('normalizeAssistantResponse falls back to legacy sources payload', () => {
  const normalized = normalizeAssistantResponse(
    {
      message: { text: 'Legacy answer' },
      sources: [
        {
          document: 'data/legacy.md',
          text: 'Legacy source excerpt',
        },
      ],
    },
    99,
  );

  assert.equal(normalized.content, 'Legacy answer');
  assert.equal(normalized.confidence, 'High');
  assert.equal(normalized.score, null);
  assert.deepEqual(normalized.citations, [
    {
      id: '99-0',
      title: 'data/legacy.md',
      snippet: 'Legacy source excerpt',
      link: '#',
    },
  ]);
});

test('normalizeAssistantResponse handles missing evidence payloads', () => {
  const normalized = normalizeAssistantResponse({}, 7);

  assert.equal(normalized.content, 'No answer returned.');
  assert.equal(normalized.confidence, 'Low');
  assert.equal(normalized.score, null);
  assert.deepEqual(normalized.citations, []);
  assert.deepEqual(normalized.evaluation, { signals: [], details: {} });
});