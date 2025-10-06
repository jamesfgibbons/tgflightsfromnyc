# VibeNet Sequence Diagrams

This document traces key request→artifact paths and UI interactions. Diagrams use Mermaid syntax for portability.

## 1) Data → Sonification Job (/vibenet/generate)

```mermaid
sequenceDiagram
  autonumber
  participant C as Client (Lovable UI)
  participant A as FastAPI (/vibenet)
  participant S as SonificationService
  participant D as Domain (completed/*)
  participant ST as Storage (S3/Supabase)

  C->>A: POST /vibenet/generate {data[], vibe_slug, controls}
  A->>S: create_sonification_service(...)
  S->>D: map_to_controls(metrics)
  S->>D: select_motifs_for_controls / by_label
  S->>D: create_sonified_midi(controls, motifs)
  D-->>S: MIDI bytes on disk
  S->>ST: put_bytes(midi)
  S->>A: {midi_key, mp3_key?, label_summary, momentum}
  A->>ST: presign URLs
  A-->>C: JobResult {midi_url, mp3_url, label_summary}
```

Notes:
- MP3 is optional (RENDER_MP3=1 + fluidsynth/ffmpeg available). Otherwise return MIDI URL only.

## 2) Board Playback (Home/Deals)

```mermaid
sequenceDiagram
  autonumber
  participant UI as Lovable Frontend
  participant B as /api/board/feed
  participant V as /vibenet/generate
  participant CDN as Public CDN (optional)

  UI->>B: GET feed?origins=JFK,EWR,LGA
  B-->>UI: rows {price, Δ%, vibe chips, spark}
  UI->>V: (on play) POST /vibenet/generate {data[], vibe_slug}
  V-->>UI: {midi_url/mp3_url}
  UI->>CDN: (stream if public)
  UI-->>User: audio playback (8–16 bars)
```

## 3) Notification → Board Badge

```mermaid
sequenceDiagram
  autonumber
  participant CR as Cron/Edge
  participant DB as Supabase
  participant API as /api/board/feed
  participant UI as Lovable Frontend

  CR->>DB: compute deltas/slope/window; insert notification_events
  UI->>API: GET board/feed
  API->>DB: fetch rows + recent events
  API-->>UI: feed with badges {PRICE_DROP, WINDOW_OPEN}
  UI-->>User: visual badges, optional audio flair
```

## 4) Local Remix (Electric Piano MIDI + Flights CSV)

```mermaid
sequenceDiagram
  autonumber
  participant CL as CLI (remix_midi_from_csv)
  participant M as completed/* + transform_midi
  participant FS as Filesystem

  CL->>CL: load CSV; derive metrics + bands + tempo
  CL->>M: select_motifs_for_controls; create_sonified_midi(base_template=<your.mid>)
  M-->>FS: write remixed .mid
  CL-->>User: output path + summary
```

