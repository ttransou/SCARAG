import { useState } from 'react';

function App() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('Ask SCARAG a question to get started.');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!query.trim()) {
      return;
    }

    setLoading(true);
    setAnswer('Thinking…');

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();
      setAnswer(data.answer || data.message?.text || 'No answer returned.');
    } catch (error) {
      setAnswer('Unable to reach the SCARAG API.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>SCARAG</h1>
        <p>Reference browser UI for grounded retrieval and answer synthesis.</p>
      </header>

      <main className="chat-card">
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

        <section className="answer-panel" aria-live="polite">
          <h2>Answer</h2>
          <p>{answer}</p>
        </section>
      </main>
    </div>
  );
}

export default App;
