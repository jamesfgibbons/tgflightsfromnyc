import { useEffect, useMemo, useRef, useState } from 'react'

type BoardRow = {
  id: string
  title: string
  data_window?: string
  vibe: { valence: number; arousal: number; tension: number }
  tempo_bpm: number
  momentum: { positive: number; neutral: number; negative: number }
  palette?: string
  last_updated?: string
  spark: number[]
}

const apiBase = '' // rewrites handle /api/* to backend

export function SplitFlapBoard({ target='keywords', limit=12, lookbackDays=30 }: { target?: 'keywords'|'entities'|'overall'; limit?: number; lookbackDays?: number }) {
  const [rows, setRows] = useState<BoardRow[]>([])
  const fetchFeed = async () => {
    const qs = new URLSearchParams({ target, limit: String(limit), lookback_days: String(lookbackDays) })
    const url = apiBase ? `${apiBase}/api/board/feed?${qs}` : `/api/board/feed?${qs}`
    const r = await fetch(url)
    const j = await r.json()
    setRows(j?.items ?? [])
  }
  useEffect(() => { fetchFeed(); }, [target, limit, lookbackDays])

  return (
    <section>
      <div className="board grid-headers">
        <div className="cell head">Title</div>
        <div className="cell head">Window</div>
        <div className="cell head">Tempo</div>
        <div className="cell head">Momentum</div>
        <div className="cell head">Trend</div>
        <div className="cell head">Val</div>
        <div className="cell head">Aro</div>
        <div className="cell head">Ten</div>
      </div>
      <div className="board">
        {rows.map((r) => (<Row key={r.id} row={r} />))}
      </div>
    </section>
  )
}

function Row({ row }: { row: BoardRow }) {
  const [flipKey, setFlipKey] = useState(0)
  const prevSparkRef = useRef<number[]>(row.spark)
  useEffect(() => {
    const prev = prevSparkRef.current?.join(',')
    const cur = row.spark?.join(',')
    if (prev !== cur) setFlipKey((k) => k + 1)
    prevSparkRef.current = row.spark
  }, [row.spark])

  const momentumLabel = useMemo(() => {
    const { positive, neutral, negative } = row.momentum
    if (positive >= neutral && positive >= negative) return 'positive'
    if (negative >= neutral && negative >= positive) return 'negative'
    return 'neutral'
  }, [row.momentum])

  return (
    <>
      <div className="cell flip" key={flipKey}>
        <div className="front">{row.title}</div>
        <div className="back">{row.title}</div>
      </div>
      <div className="cell small">{row.data_window ?? '—'}</div>
      <div className="cell small tempo">{row.tempo_bpm} BPM</div>
      <div className={`cell chip ${momentumLabel}`}>{momentumLabel}</div>
      <Spark spark={row.spark} />
      <div className="cell tiny">{row.vibe.valence.toFixed(2)}</div>
      <div className="cell tiny">{row.vibe.arousal.toFixed(2)}</div>
      <div className="cell tiny">{row.vibe.tension.toFixed(2)}</div>
    </>
  )
}

function Spark({ spark }: { spark: number[] }) {
  return (
    <div className="spark">
      {spark.map((v, i) => (
        <div key={i} className="bar" style={{ height: `${Math.max(6, Math.round(v * 36))}px` }} />
      ))}
    </div>
  )
}
