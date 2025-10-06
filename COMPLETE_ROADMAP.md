# Complete Roadmap (Lovable + Railway)

Status: 2025-10-05

Overall MVP target: **2025-10-12** (Week 2). Post-launch growth cycles continue through Month 1.

## Phase 1 – Foundations (✅ 100%)
- Backend API online (Railway) with `/api/board/feed`, `/api/book/*`, `/api/notifications/*`, `/vibenet/generate`
- Supabase schema migrated (`000_init_schema.sql` … `010_notification_engine.sql`)
- Destination ontology + palette routing in place

## Phase 2 – Front-End Integration (🚧 55% in progress)
**Duration:** Sprint 2 (Oct 5–12)  
**Goal:** Ship Lovable MVP with live data and sonification

### 🔴 High Priority
- [ ] Add Best-Time snapshot rail (5–8 routes) below hero
- [ ] Wire split-flap board to `/api/board/feed`
- [ ] Overlay badges from `/api/notifications/board`
- [ ] Build `/routes/[origin]/[dest]` page
- [ ] Integrate `<BestTimeSummary>` component
- [ ] Add `<LeadTimeCurve>` visualization
- [ ] Implement “Play the curve” (q50 slice → `generateAutoVibe`)
- [ ] Add event timeline (`/api/notifications/route` last 7 days)
- [ ] Inject JSON-LD per route

### 🟡 Medium Priority
- [ ] Featured Mixes (6–10 MP3s)
  - Caribbean ×3, West Coast ×2, Europe ×2, Asia-Pacific ×2
  - Upload to CDN, update `public/featured_mixes.json`
- [ ] Hook implementations
  - `useBoardData` (merge rows + badges)
  - `useRouteBadges` (timeline)
  - Badge UI components (lime/cyan/magenta pills)

Estimated effort: ~12 hours (front-end dev) + render time for mixes.

## Phase 3 – Distribution & SEO (⏳ 0%)
**Duration:** Sprint 3 (post-MVP)  
**Target:** 2025-10-15

### 3.1 Embed Widget
- [ ] Create `/embed` route (responsive board)
- [ ] Support URL params (`origins`, `limit`, `theme`)
- [ ] Publish `postMessage` API + iframe snippet generator

### 3.2 Programmatic SEO
- [ ] Route template reused for `/best-time/[origin]-to-[dest]`
- [ ] Generate top 50 NYC route pairs
- [ ] Add JSON-LD per page
- [ ] Generate `sitemap.xml` + optimize `robots.txt`

### 3.3 Meta / OG
- [ ] Dynamic OG images per route
- [ ] Twitter Cards
- [ ] Update `SEOHelmet`

## Phase 4 – Growth & Analytics (⏳ 0%)
**Duration:** Sprint 4 (Month 1)  
**Target:** 2025-10-22

### 4.1 Analytics
- [ ] Event tracking (play, route view, deal click)
- [ ] Audio engagement metrics
- [ ] View → play → external booking funnel
- [ ] Internal dashboard (Supabase SQL + Metabase or similar)

### 4.2 AI Recommendations
- [ ] Personal route suggestions based on listening
- [ ] Price alert preferences + email notifications

### 4.3 Growth Loops
- [ ] Audiograms for social
- [ ] Weekly newsletter (top deals)
- [ ] Referral system

## Critical Path to MVP

### Week 1 (Oct 5–8)
1. ✅ Railway smoke tests (all endpoints)
2. 🟡 Home integration (board + badges + snapshot rail)
3. 🟡 Route detail (summary, curve, play, timeline)
4. 🔄 Replace mock data with live API hooks

### Week 2 (Oct 9–12)
1. Generate Featured Mixes MP3s and upload to CDN
2. SEO pass (JSON-LD, metadata)
3. Performance audit (Lighthouse ≥90 mobile)
4. Accessibility audit (WCAG AA)
5. 🚀 **MVP Launch**

## KPI Targets

### Week 1 Post-Launch
- Play rate > 20% of board views
- Median listen time > 15 seconds
- Route CTR > 10%

### Month 1
- ≥2 partner embeds
- ≥500 organic sessions
- Return users ≥ 15%

## Dependencies / Risks

**Critical:**
1. Railway API uptime (Phase 2 blocked if endpoints fail)
2. CDN configured for Featured Mixes
3. Notification engine migration applied

**Risks & Mitigation:**
- API downtime → fallback content (cached deals, placeholder mixes)
- Audio generation latency → pre-render top routes, show progress UI
- SEO competition → focus on long-tail route/month combinations

## Immediate Action Log

**Oct 5:**
- [ ] Run Railway smoke tests & document results
- [ ] Start Home/Route integration if tests pass; otherwise coordinate backend

**Oct 6:**
- [ ] Finish board rail + snapshot
- [ ] Implement route detail page
- [ ] Create notification hooks

**This Week:**
- [ ] Complete all Phase 2 integration tasks
- [ ] Render Featured Mixes
- [ ] Prepare launch checklist

## References
- `PRODUCTION_SPEC.md`
- `API_INTEGRATION_GUIDE.md`
- `SIGNATURE_POLISH.md`
- Audible Intelligence Fabric™ Codex

