# Agentic B2C Demand Generation + Sonification (v4)

This document aligns the agentic strategy for SERPRadio’s public‑facing experience and the supporting stack.

## Goals
- Ship a fast, non‑expert‑friendly MVP that looks great and streams live data
- Use Vercel (Vite) for UI, Railway for backend, Supabase for data
- Grow into a programmatic SEO engine (templates + data + audio embeds)

## System Pillars
- Lovable.dev: lightweight landing shell for SERPRadio.com (embeds Vercel views)
- Vercel Vite: split‑flap board, map, overlays, chat (Vercel AI SDK optional)
- Railway FastAPI: orchestrates routes/quotes, board feed, xAI Grok summaries
- Supabase: routes + quotes store, optional web context summaries

## Agentic Loops
- Prompt intake → LLM batch (optional) → parse + upsert → board/map render
- User interactions → “impressions” → feed back into VibeNet presets
- Context fetch (Grok) → overlay badges/panels → link‑outs for engagement

## MVP Surface
- Split‑flap board powered by `/api/board/feed` (dataset)
- Travel endpoints from Supabase (`routes_nyc`, `price_quotes_latest`)
- Optional chat (Edge) for queries; context “i” button for summaries

## Scale Path
- Programmatic SEO (Next.js SSG/ISR) for route hubs and tools
- Preset audio for instant playback on generated pages
- On‑the‑fly sonification for interactive tools (VibeNet endpoints)

## Ops
- KV/ETag caching on board feed
- RLS policies for read‑only anon SELECT (if public API)
- Railway monitoring + simple Prom metrics

## Next Steps
- Add `/api/travel/context` reading `web_context_summaries`
- Map explore page with arcs + citations overlay
- Route annotations + moderation UI for editorial control

Use this doc as the blueprint for prioritizing features and ensuring every surface ties back to measurable demand generation.
