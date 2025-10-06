import { useState } from 'react'
import { SplitFlapBoard } from './components/SplitFlapBoard'

export default function App() {
  const [target, setTarget] = useState<'keywords'|'entities'|'overall'>('keywords')
  return (
    <div className="wrap">
      <h1>SERPRadio v4 • Split‑Flap</h1>
      <div className="tabs">
        {(['keywords','entities','overall'] as const).map(t => (
          <button key={t} className={t===target? 'tab active':'tab'} onClick={()=>setTarget(t)}>{t}</button>
        ))}
      </div>
      <SplitFlapBoard target={target} limit={12} lookbackDays={30} />
    </div>
  )
}
