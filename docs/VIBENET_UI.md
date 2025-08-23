# VibeNet UI Integration (Lovable)

This guide focuses on a design‑agnostic control panel (radio‑style) and API wiring. You own the broader site design.

## Controls Panel (suggested fields)
- Vibe: radios (`caribbean_kokomo`, `synthwave_midnight`, `arena_anthem`)
- Data input: file upload (CSV) or paste numeric JSON
- Bars: 8 / 16 / 32
- Tempo (optional): number input; leave blank for auto
- Generate button + status

## Fetch APIs
- List vibes:
```ts
const vibes = await fetch('/vibenet/vibes').then(r=>r.json());
```
- Generate (numeric array):
```ts
await fetch('/vibenet/generate', {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    vibe_slug: state.vibe || 'synthwave_midnight',
    data: state.values, // number[]
    controls: { bars: state.bars || 16, tempo_hint: state.tempo || null }
  })
}).then(r=>r.json()).then(setJob);
```

## React skeleton (TSX)
```tsx
function RadioControlsPanel(){
  const [vibe,setVibe]=useState('synthwave_midnight');
  const [bars,setBars]=useState(16);
  const [tempo,setTempo]=useState<number|''>('');
  const [values,setValues]=useState<number[]>([0.1,0.3,0.6,0.2,0.8,0.4]);
  const [job,setJob]=useState<any>(null);
  const gen=async()=>{
    const body={vibe_slug:vibe,data:values,controls:{bars,tempo_hint:tempo||null}};
    const res=await fetch('/vibenet/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    setJob(await res.json());
  };
  return (
    <div>
      <fieldset>
        <label><input type="radio" checked={vibe==='caribbean_kokomo'} onChange={()=>setVibe('caribbean_kokomo')}/> Caribbean</label>
        <label><input type="radio" checked={vibe==='synthwave_midnight'} onChange={()=>setVibe('synthwave_midnight')}/> Synthwave</label>
        <label><input type="radio" checked={vibe==='arena_anthem'} onChange={()=>setVibe('arena_anthem')}/> Arena</label>
      </fieldset>
      <label>Bars <input type="number" value={bars} onChange={e=>setBars(parseInt(e.target.value,10)||16)} /></label>
      <label>Tempo <input type="number" value={tempo} onChange={e=>setTempo(e.target.value?parseInt(e.target.value,10):'')} /></label>
      <textarea value={JSON.stringify(values)} onChange={e=>{try{setValues(JSON.parse(e.target.value))}catch{}}} />
      <button onClick={gen}>Generate</button>
      {job?.mp3_url && <audio controls src={job.mp3_url} />}
    </div>
  );
}
```

## CSV support (optional)
- Parse client‑side (PapaParse) to a primary numeric column.
- Or POST CSV to an upload endpoint, then fetch processed rows and map to numeric array.

## Notes
- Leave styling to your design system; only the control semantics are suggested here.
- MP3 rendering requires `RENDER_MP3=1` and system deps. If disabled, use `midi_url` + WebAudio/Tone.js.
- Use `/api/vibe/screenshot` for palette derivation from screenshots (artist/title) if needed.

