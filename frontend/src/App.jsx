import { useState } from 'react';

const INITIAL_MESSAGE = {
  id: 1,
  role: 'assistant',
  content: 'Ask SCARAG a question to get started. I’ll surface the answer and the evidence behind it.',
  citations: [],
  confidence: 'Ready',
  score: null,
  feedback: null,
};

const FAQ_ITEMS = [
  {
    id: 'faq-1',
    question: 'How does SCARAG answer questions?',
    answer: 'SCARAG retrieves relevant evidence from your corpus and synthesizes a grounded response with citations and transparency signals.',
  },
  {
    id: 'faq-2',
    question: 'What should I expect from the evidence drawer?',
    answer: 'The evidence drawer surfaces the retrieved sources, confidence context, and any low-signal or near-match flags for review.',
  },
  {
    id: 'faq-3',
    question: 'How can this FAQ be customized?',
    answer: 'Replace these sample entries with implementation-specific questions, policies, or onboarding guidance.',
  },
];

function App() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [theme, setTheme] = useState('default');
  const [feedbackDrafts, setFeedbackDrafts] = useState({});
  const [activeView, setActiveView] = useState('chat');

  const activeMessage = [...messages].reverse().find((message) => message.role === 'assistant') || messages[messages.length - 1];

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || loading) {
      return;
    }

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: trimmedQuery,
    };

    const assistantPlaceholder = {
      id: Date.now() + 1,
      role: 'assistant',
      content: 'Thinking…',
      citations: [],
      confidence: 'Reviewing sources…',
      score: null,
      feedback: null,
    };

    setMessages((previousMessages) => [...previousMessages, userMessage, assistantPlaceholder]);
    setQuery('');
    setLoading(true);
    setDrawerOpen(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmedQuery }),
      });

      const data = await response.json();
      const answer = data.answer || data.message?.text || 'No answer returned.';
      const citations = Array.isArray(data.citations)
        ? data.citations
        : Array.isArray(data.sources)
          ? data.sources
          : [];

      const nextAssistantMessage = {
        ...assistantPlaceholder,
        content: answer,
        citations: citations.slice(0, 5).map((citation, index) => ({
          id: `${assistantPlaceholder.id}-${index}`,
          title: citation.title || citation.document || `Source ${index + 1}`,
          snippet: citation.snippet || citation.text || citation.content || 'Retrieved evidence will appear here.',
          link: citation.link || '#',
        })),
        confidence: data.confidence || (citations.length ? 'High' : 'Low'),
        score: data.score ?? null,
      };

      setMessages((previousMessages) => previousMessages.map((message) => (message.id === assistantPlaceholder.id ? nextAssistantMessage : message)));
    } catch (error) {
      setMessages((previousMessages) => previousMessages.map((message) =>
        message.id === assistantPlaceholder.id
          ? {
              ...assistantPlaceholder,
              content: 'Unable to reach the SCARAG API.',
              confidence: 'Offline',
              citations: [{ id: `${assistantPlaceholder.id}-offline`, title: 'Connection issue', snippet: 'The backend did not respond.', link: '#' }],
            }
          : message,
      ));
    } finally {
      setLoading(false);
    }
  }

  function handleFeedback(messageId, value) {
    setMessages((previousMessages) => previousMessages.map((message) =>
      message.id === messageId ? { ...message, feedback: value } : message,
    ));

    if (value === 'down') {
      setFeedbackDrafts((previousDrafts) => ({
        ...previousDrafts,
        [messageId]: previousDrafts[messageId] || '',
      }));
      return;
    }

    setFeedbackDrafts((previousDrafts) => {
      const nextDrafts = { ...previousDrafts };
      delete nextDrafts[messageId];
      return nextDrafts;
    });
  }

  function renderAnswerContent(text) {
    const lines = text.split('\n');
    const rendered = [];
    let listItems = [];

    function flushList() {
      if (listItems.length) {
        rendered.push(
          <ul className="answer-list" key={`list-${rendered.length}`}>
            {listItems.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
          </ul>,
        );
        listItems = [];
      }
    }

    lines.forEach((line, index) => {
      const trimmed = line.trim();
      if (!trimmed) {
        flushList();
        return;
      }

      const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)$/);
      if (headingMatch) {
        flushList();
        const level = Math.min(headingMatch[1].length, 3);
        const HeadingTag = `h${level}`;
        rendered.push(<HeadingTag key={`heading-${index}`} className="answer-heading">{formatInlineText(headingMatch[2])}</HeadingTag>);
        return;
      }

      const bulletMatch = trimmed.match(/^[-*]\s+(.*)$/);
      if (bulletMatch) {
        listItems.push(formatInlineText(bulletMatch[1]));
        return;
      }

      flushList();
      rendered.push(<p key={`paragraph-${index}`} className="answer-paragraph">{formatInlineText(trimmed)}</p>);
    });

    flushList();
    return rendered;
  }

  function formatInlineText(text) {
    const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);

    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={`${part}-${index}`}>{part.slice(1, -1)}</code>;
      }
      return <span key={`${part}-${index}`}>{part}</span>;
    });
  }

  return (
    <div className={`app-shell theme-${theme}`}>
      <aside className={`sidebar ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="sidebar-top">
          <button className="icon-button" onClick={() => setSidebarCollapsed((value) => !value)} aria-label="Toggle sidebar">
            ☰
          </button>
          <div className="brand-block">
            <p className="eyebrow">SCARAG</p>
            <h1>Grounded AI</h1>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          <button type="button" className={`nav-link ${activeView === 'chat' ? 'active' : ''}`} onClick={() => setActiveView('chat')}>
            New Chat
          </button>
          <button type="button" className="nav-link">Chat History</button>
          <button type="button" className={`nav-link ${activeView === 'faq' ? 'active' : ''}`} onClick={() => setActiveView('faq')}>
            FAQ
          </button>
          <button type="button" className="nav-link">Support</button>
        </nav>

        <div className="sidebar-card">
          <p className="eyebrow">API health</p>
          <p className="status-pill">Online</p>
          <p className="helper-text">Responses stay linked to retrieved evidence.</p>
        </div>
      </aside>

      <main className="workspace-panel">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">Transparent RAG experience</p>
            <h2>{activeView === 'faq' ? 'FAQ' : 'Ask SCARAG'}</h2>
          </div>
          <div className="header-actions">
            <button
              type="button"
              className="ghost-button"
              onClick={() => setTheme((currentTheme) => {
                const order = ['default', 'light', 'dark'];
                const nextIndex = (order.indexOf(currentTheme) + 1) % order.length;
                return order[nextIndex];
              })}
            >
              Theme: {theme}
            </button>
            <button type="button" className="ghost-button" onClick={() => setDrawerOpen((value) => !value)}>
              {drawerOpen ? 'Hide evidence' : 'Show evidence'}
            </button>
          </div>
        </header>

        {activeView === 'faq' ? (
          <section className="faq-view" aria-live="polite">
            <div className="faq-intro">
              <p className="eyebrow">Customizable template</p>
              <h3>Frequently asked questions</h3>
              <p>Replace these starter entries with implementation-specific guidance for your users.</p>
            </div>
            <div className="faq-list">
              {FAQ_ITEMS.map((item) => (
                <article key={item.id} className="faq-card">
                  <h4>{item.question}</h4>
                  <p>{item.answer}</p>
                </article>
              ))}
            </div>
            <button type="button" className="ghost-button faq-return" onClick={() => setActiveView('chat')}>
              Return to chat
            </button>
          </section>
        ) : (
          <>
            <section className="conversation-stack" aria-live="polite">
              {messages.map((message) => (
                <article key={message.id} className={`message-card ${message.role}`}>
                  <div className="message-meta">
                    <span className="message-role">{message.role === 'user' ? 'You' : 'SCARAG'}</span>
                    {message.role === 'assistant' && (
                      <div className="message-badges">
                        {message.confidence && <span className="badge">{message.confidence}</span>}
                        {message.score !== null && <span className="badge subtle">Score {message.score}</span>}
                      </div>
                    )}
                  </div>

                  {message.role === 'assistant' ? (
                    <div className="answer-body">
                      {renderAnswerContent(message.content)}
                    </div>
                  ) : (
                    <p className="user-message">{message.content}</p>
                  )}

                  {message.role === 'assistant' && (
                    <>
                      <div className="message-actions">
                        <button type="button" className={`feedback-button ${message.feedback === 'up' ? 'active' : ''}`} onClick={() => handleFeedback(message.id, 'up')}>
                          👍
                        </button>
                        <button type="button" className={`feedback-button ${message.feedback === 'down' ? 'active' : ''}`} onClick={() => handleFeedback(message.id, 'down')}>
                          👎
                        </button>
                      </div>

                      {message.feedback === 'down' && (
                        <div className="feedback-entry">
                          <label htmlFor={`feedback-${message.id}`}>What went wrong?</label>
                          <textarea
                            id={`feedback-${message.id}`}
                            value={feedbackDrafts[message.id] || ''}
                            onChange={(event) => setFeedbackDrafts((previousDrafts) => ({
                              ...previousDrafts,
                              [message.id]: event.target.value,
                            }))}
                            placeholder="Share what felt inaccurate or unhelpful"
                          />
                          <p className="feedback-note">Future implementation: wire this field to feedback capture and storage.</p>
                        </div>
                      )}
                    </>
                  )}
                </article>
              ))}
            </section>

            <form onSubmit={handleSubmit} className="prompt-form">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ask a question about your corpus"
                aria-label="Question"
              />
              <button type="submit" disabled={loading}>
                {loading ? 'Sending…' : 'Ask'}
              </button>
            </form>
          </>
        )}
      </main>

      <aside className={`evidence-drawer ${drawerOpen ? 'open' : 'collapsed'}`}>
        <div className="drawer-header">
          <div>
            <p className="eyebrow">Evidence</p>
            <h3>Trace</h3>
          </div>
          <button type="button" className="icon-button" onClick={() => setDrawerOpen((value) => !value)} aria-label="Toggle evidence drawer">
            ↔
          </button>
        </div>

        <div className="drawer-content">
          {activeMessage?.citations?.length ? (
            activeMessage.citations.map((citation) => (
              <article key={citation.id} className="citation-card">
                <h4>{citation.title}</h4>
                <p>{citation.snippet}</p>
                <a href={citation.link} target="_blank" rel="noreferrer">Open source</a>
              </article>
            ))
          ) : (
            <div className="empty-state">
              <p>No evidence has been surfaced yet.</p>
              <span>Retrieved citations and low-confidence flags will appear here.</span>
            </div>
          )}

          <div className="drawer-metrics">
            <div className="metric-card">
              <span>Confidence</span>
              <strong>{activeMessage?.confidence || 'Unknown'}</strong>
            </div>
            <div className="metric-card">
              <span>Score</span>
              <strong>{activeMessage?.score ?? '—'}</strong>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}

export default App;
