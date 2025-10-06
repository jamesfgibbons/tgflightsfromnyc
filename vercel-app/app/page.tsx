import Link from 'next/link';

export default function Page() {
  return (
    <section>
      <h1>Flight Deal Symphony • VibeNet Concepts</h1>
      <p>Three small demos deployed on Vercel using the AI SDK, aligned with the Split‑Flap board and FastAPI backend.</p>
      <ul className="cards">
        <li>
          <h3>Split‑Flap Classic</h3>
          <p>Retro board reading `/api/board/feed` with KV caching and palette/vibe controls.</p>
          <Link href="/embed">Open</Link>
        </li>
        <li>
          <h3>Radio Tuner</h3>
          <p>Dial through canonical NYC routes, watch flips and volatility, and queue annotations.</p>
          <Link href="/radio">Open</Link>
        </li>
        <li>
          <h3>Deal Composer</h3>
          <p>Chat with tools (routes, prices, board) using Vercel AI SDK, streaming responses.</p>
          <Link href="/composer">Open</Link>
        </li>
      </ul>
    </section>
  );
}

