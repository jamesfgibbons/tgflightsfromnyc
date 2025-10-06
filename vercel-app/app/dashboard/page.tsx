"use client";
import useSWR from 'swr';
import { useMemo, useState } from 'react';

type Route = { origin: string; destination: string; destination_name?: string; popularity_score?: number };
type Quote = { origin: string; destination: string; window_days?: number; price_low_usd?: number; price_high_usd?: number; brands?: string[]; created_at?: string };

const fetcher = (url: string) => fetch(url).then(r => r.json());

export default function Dashboard() {
  const [origin, setOrigin] = useState<'JFK'|'LGA'|'EWR'>('JFK');
  const { data: routes } = useSWR<{ total:number; items: Route[] }>(`/api/travel/routes?origin=${origin}&limit=200`, fetcher);
  const { data: quotes } = useSWR<{ total:number; items: Quote[] }>(`/api/travel/price_quotes_latest?origin=${origin}&limit=200`, fetcher);

  const list = (routes?.items ?? []).slice().sort((a,b)=> (b.popularity_score||0)-(a.popularity_score||0));
  const mapQuotes = useMemo(() => {
    const m = new Map<string, Quote>();
    for (const q of (quotes?.items ?? [])) m.set(`${q.origin}-${q.destination}`, q);
    return m;
  }, [quotes]);

  return (
    <section>
      <h1>VibeNet QA • Routes + Latest Quotes</h1>
      <p className="meta">Pick an origin and scan top routes with latest parsed quotes. Use this to prototype split‑flap and composer prompts.</p>
      <div className="toolbar">
        {(['JFK','LGA','EWR'] as const).map(o => (
          <button key={o} className={o===origin? 'tab active':'tab'} onClick={()=>setOrigin(o)}>{o}</button>
        ))}
        <span className="muted">Routes: {routes?.total ?? 0} • Quotes: {quotes?.total ?? 0}</span>
      </div>
      <div className="table">
        <div className="thead">
          <div>Origin</div>
          <div>Destination</div>
          <div>Name</div>
          <div>Low</div>
          <div>High</div>
          <div>Brands</div>
          <div>Updated</div>
        </div>
        {list.slice(0, 200).map((r, i) => {
          const q = mapQuotes.get(`${r.origin}-${r.destination}`);
          return (
            <div key={`${r.origin}-${r.destination}-${i}`} className="trow">
              <div>{r.origin}</div>
              <div>{r.destination}</div>
              <div>{r.destination_name ?? '—'}</div>
              <div>{q?.price_low_usd ? `$${q.price_low_usd}` : '—'}</div>
              <div>{q?.price_high_usd ? `$${q.price_high_usd}` : '—'}</div>
              <div className="muted">{(q?.brands ?? []).join(', ') || '—'}</div>
              <div className="muted">{q?.created_at ? new Date(q.created_at).toLocaleDateString() : '—'}</div>
            </div>
          );
        })}
        {!list.length && <div className="muted" style={{padding:10}}>No routes for {origin} yet.</div>}
      </div>
    </section>
  );
}

