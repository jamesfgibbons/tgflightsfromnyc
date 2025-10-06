"use client";
import { useEffect, useMemo, useRef, useState } from 'react';
import useSWR from 'swr';
import { clsx } from 'clsx';

type BoardRow = {
  id: string;
  title: string;
  data_window?: string;
  vibe: { valence: number; arousal: number; tension: number };
  tempo_bpm: number;
  momentum: { positive: number; neutral: number; negative: number };
  palette: string;
  last_updated?: string;
  spark: number[];
};

type Route = { origin: string; destination: string; destination_name?: string; popularity_score?: number };

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function EmbedPage({ searchParams }: any) {
  const target = searchParams?.target ?? 'keywords';
  const limit = Number(searchParams?.limit ?? 12);
  const lookback_days = Number(searchParams?.lookback_days ?? 30);
  const palette_slug = searchParams?.palette_slug ?? '';
  const refreshMs = Number(searchParams?.refresh_ms ?? 45000);
  const adminMode = searchParams?.admin === '1';
  const seedMessage = (typeof window !== 'undefined' && localStorage.getItem('vibenet:msg')) || searchParams?.message || '';

  const { data, mutate } = useSWR(
    `/api/board/feed?target=${encodeURIComponent(target)}&limit=${limit}&lookback_days=${lookback_days}&palette_slug=${encodeURIComponent(palette_slug)}`,
    fetcher,
    { revalidateOnFocus: false }
  );
  const { data: routesData } = useSWR<{ total: number; items: Route[] }>(`/api/travel/routes`, fetcher);

  // Polling with visibility pause
  useEffect(() => {
    let t: any;
    function loop() {
      if (document.visibilityState === 'visible') mutate();
      t = setTimeout(loop, refreshMs);
    }
    loop();
    return () => clearTimeout(t);
  }, [mutate, refreshMs]);

  const items: BoardRow[] = data?.items ?? [];
  const routes = routesData?.items ?? [];
  const topByOrigin = groupTopByOrigin(routes, 5);

  const [adHocMsg, setAdHocMsg] = useState<string>(seedMessage);
  useEffect(() => {
    if (adHocMsg) localStorage.setItem('vibenet:msg', adHocMsg);
  }, [adHocMsg]);

  return (
    <section className="grid">
      <div className="main">
        <h1>Split‑Flap Board</h1>
        <p className="meta">Target: {target} • Items: {limit} • Window: {lookback_days}d</p>
        <div className="board">
          {items.map((row) => (
            <Row key={row.id} row={row} />
          ))}
        </div>
        <DealsTicker />
        <TraditionalInfo routes={routes} />
      </div>
      <aside className="side">
        <h3>Top Routes • NYC</h3>
        <TopRoutes origin="JFK" items={topByOrigin['JFK'] ?? []} />
        <TopRoutes origin="LGA" items={topByOrigin['LGA'] ?? []} />
        <TopRoutes origin="EWR" items={topByOrigin['EWR'] ?? []} />
        <div className="adhoc">
          <h4>Ad‑hoc Messaging</h4>
          {adminMode ? (
            <textarea value={adHocMsg} onChange={(e) => setAdHocMsg(e.target.value)} placeholder="Enter internal message…" />
          ) : (
            <p className="muted">{adHocMsg || '—'}</p>
          )}
        </div>
      </aside>
    </section>
  );
}

function Row({ row }: { row: BoardRow }) {
  const [flipKey, setFlipKey] = useState(0);
  const prevSparkRef = useRef<number[]>(row.spark);
  useEffect(() => {
    const prev = prevSparkRef.current?.join(',');
    const cur = row.spark?.join(',');
    if (prev !== cur) setFlipKey((k) => k + 1);
    prevSparkRef.current = row.spark;
  }, [row.spark]);

  const momentumLabel = useMemo(() => {
    const { positive, neutral, negative } = row.momentum;
    if (positive >= neutral && positive >= negative) return 'positive';
    if (negative >= neutral && negative >= positive) return 'negative';
    return 'neutral';
  }, [row.momentum]);

  return (
    <div className={clsx('row', row.palette)}>
      <div key={flipKey} className="cell flip">
        <div className="front">{row.title}</div>
        <div className="back">{row.title}</div>
      </div>
      <div className="cell small">{row.data_window ?? '—'}</div>
      <div className="cell small tempo">{row.tempo_bpm} BPM</div>
      <div className={clsx('cell chip', momentumLabel)}>{momentumLabel}</div>
      <Spark spark={row.spark} />
      <div className="cell tiny">{row.vibe.valence.toFixed(2)}</div>
      <div className="cell tiny">{row.vibe.arousal.toFixed(2)}</div>
      <div className="cell tiny">{row.vibe.tension.toFixed(2)}</div>
    </div>
  );
}

function Spark({ spark }: { spark: number[] }) {
  return (
    <div className="spark">
      {spark.map((v, i) => (
        <div key={i} className="bar" style={{ height: `${Math.max(6, Math.round(v * 36))}px` }} />
      ))}
    </div>
  );
}

function groupTopByOrigin(items: Route[], per = 5) {
  const groups: Record<string, Route[]> = { JFK: [], LGA: [], EWR: [] };
  for (const r of items) {
    const o = (r.origin || '').toUpperCase();
    if (!groups[o]) continue;
    groups[o].push(r);
  }
  for (const k of Object.keys(groups)) {
    const list = groups[k];
    list.sort((a, b) => (b.popularity_score || 0) - (a.popularity_score || 0));
    groups[k] = list.slice(0, per);
  }
  return groups;
}

function TopRoutes({ origin, items }: { origin: string; items: Route[] }) {
  return (
    <div className="toproutes">
      <div className="heading">{origin}</div>
      <ul>
        {items.map((r, i) => (
          <li key={`${origin}-${i}`}>
            <span className="code">{origin}</span>
            <span className="arrow">→</span>
            <span className="code">{r.destination}</span>
            <span className="name">{r.destination_name ?? ''}</span>
          </li>
        ))}
        {!items.length && <li className="muted">No routes yet</li>}
      </ul>
    </div>
  );
}

function TraditionalInfo({ routes }: { routes: Route[] }) {
  const sample = routes.slice(0, 8);
  return (
    <div className="traditional">
      <h3>Traditional Routes & Info</h3>
      <div className="table">
        <div className="thead">
          <div>Origin</div>
          <div>Destination</div>
          <div>Name</div>
          <div>Notes</div>
        </div>
        {sample.map((r, i) => (
          <div key={i} className="trow">
            <div>{r.origin}</div>
            <div>{r.destination}</div>
            <div>{r.destination_name ?? '—'}</div>
            <div className="muted">High‑volume route</div>
          </div>
        ))}
        {!sample.length && <div className="muted">No route data available.</div>}
      </div>
    </div>
  );
}

function DealsTicker() {
  const [i, setI] = useState(0);
  const [msgs, setMsgs] = useState<string[]>([]);
  useEffect(() => {
    let alive = true;
    // Pull a few common quotes to show rotating deals; fallback text if none
    Promise.all([
      fetch(`/api/travel/price_quotes?origin=JFK`).then((r) => r.json()).catch(() => ({ items: [] })),
      fetch(`/api/travel/price_quotes?origin=LGA`).then((r) => r.json()).catch(() => ({ items: [] })),
      fetch(`/api/travel/price_quotes?origin=EWR`).then((r) => r.json()).catch(() => ({ items: [] })),
    ]).then(([a, b, c]) => {
      if (!alive) return;
      const all = [...(a.items || []), ...(b.items || []), ...(c.items || [])];
      const top = all.slice(0, 10);
      const m = top.map((q: any) => `${q.origin}→${q.destination}: $${q.price} ${q.brand ? '• ' + q.brand : ''}`);
      setMsgs(m.length ? m : ['Deals update pending…', 'Routes syncing — check back shortly.']);
    });
    return () => {
      alive = false;
    };
  }, []);
  useEffect(() => {
    const t = setInterval(() => setI((x) => (msgs.length ? (x + 1) % msgs.length : 0)), 4000);
    return () => clearInterval(t);
  }, [msgs]);
  const text = msgs[i] ?? '';
  return (
    <div className="ticker">
      <div className="dot" />
      <div className="text">{text}</div>
    </div>
  );
}
