"use client";
import { useChat } from 'ai/react';

export default function ComposerPage() {
  const { input, setInput, handleInputChange, handleSubmit, messages, isLoading } = useChat({ api: '/api/chat' });
  return (
    <section className="chat">
      <h1>Deal Composer • Vercel AI SDK</h1>
      <div className="messages">
        {messages.map((m) => (
          <div key={m.id} className={m.role === 'user' ? 'msg user' : 'msg bot'}>
            {m.content}
          </div>
        ))}
        {isLoading && <div className="msg bot">Thinking…</div>}
      </div>
      <form onSubmit={handleSubmit} className="composer">
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Ask for cheapest NYC→MIA next month, or summarize board…"
        />
        <button type="submit">Send</button>
      </form>
      <p className="hint">The model can call tools: routes, price quotes, and board feed. It streams results and cites actions inline.</p>
    </section>
  );
}

