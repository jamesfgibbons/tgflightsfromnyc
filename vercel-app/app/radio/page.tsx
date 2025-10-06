"use client";
import { useEffect, useMemo, useState } from 'react';
import useSWR from 'swr';

type Route = { origin: string; destination: string; destination_name?: string };

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function RadioPage() {
  const { data: routes } = useSWR<{ total: number; items: Route[] }>(`/api/travel/routes`, fetcher);
  const list = (routes?.items ?? []).map((r) => ({ ...r, label: `${r.origin} → ${r.destination}${r.destination_name ? ` (${r.destination_name})` : ''}` }));
  const [idx, setIdx] = useState(0);
  const cur = list[idx % Math.max(list.length, 1)] ?? { origin: 'JFK', destination: 'LAX', label: 'JFK → LAX' } as any;

  const onTune = (e: React.ChangeEvent<HTMLInputElement>) => setIdx(parseInt(e.target.value, 10));

  const [flipKey, setFlipKey] = useState(0);
  useEffect(() => setFlipKey((k) => k + 1), [cur.label]);

  const [quotes, setQuotes] = useState<any[]>([]);
  useEffect(() => {
    const q = new URLSearchParams({ origin: cur.origin, destination: cur.destination });
    fetch(`/api/travel/price_quotes?` + q.toString())
      .then((r) => r.json())
      .then((d) => setQuotes(d?.items ?? []))
      .catch(() => setQuotes([]));
  }, [cur.origin, cur.destination]);

  const best = useMemo(() => quotes[0], [quotes]);

  return (
    <section>
      <h1>Radio Tuner • NYC Canonical Routes</h1>
      <div className="tuner">
        <div className="dial">
          <input type="range" min={0} max={Math.max(list.length - 1, 0)} value={idx} onChange={onTune} />
          <div className="station">
            <span className="mono">TUNED</span>
            <span className="flip" key={flipKey}>{cur.label}</span>
          </div>
        </div>
        <div className="panel">
          <div>
            <div className="label">Origin</div>
            <div className="value">{cur.origin}</div>
          </div>
          <div>
            <div className="label">Destination</div>
            <div className="value">{cur.destination}</div>
          </div>
          <div>
            <div className="label">Best Quote</div>
            <div className="value">{best ? `$${best.price} • ${best.airline ?? '—'}` : '—'}</div>
          </div>
        </div>
      </div>
      <p className="hint">Tip: Use this to audition routes and queue an annotation. Admin routes can trigger Grok summaries via backend cron.</p>
    </section>
  );
}
