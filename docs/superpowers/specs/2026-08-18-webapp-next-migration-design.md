# Design Spec: Next.js Web Frontend Migration

**Date:** 2026-08-18  
**Author:** Hermes Agent  
**Status:** Approved for spec — pending user review  
**Phase:** Phase 1 (Core Catalog + SEO)

---

## 1. Decision Record

| Decision | Value | Rationale |
|---|---|---|
| Repository model | **Monorepo (Approach A)** | Parallel dev in same repo; single CI/CD; clean `frontend/` vs `webapp-next/` boundary |
| Web framework | **Next.js 15 (App Router) + TypeScript + React** | SSR/SSG native, edge-deployable, TypeScript safety |
| Data access | **FastAPI only** | No direct DB access from web tier; API-first boundary preserved |
| Rendering | **SSR + ISR** | Public/SEO routes use SSG+ISR; search/filter use SSR per-request |
| Auth strategy | **FastAPI session forwarding** (interface contract in Phase 1) | No new auth authority; Next.js forwards cookies to FastAPI `/auth/*` during SSR |
| Phase 1 scope | **Core catalog + SEO** | Homepage, whisky listing, whisky detail, distillery pages, SEO metadata |
| Phase 1 deferred | Tasting notes, flavor radar, similarity, auth-gated features | Extensible architecture ready; not in first release |

---

## 2. Architecture

```
maltradar.com →  Next.js (webapp-next/)
                          │
                          │ HTTPS + API
                          ▼
                     FastAPI (backend/)
                          │
                          ▼
                  production.db / domain layer
```

**Key principle:** The new Next.js web tier is a **pure presentation layer**. It forwards to the existing FastAPI backend for all data, including auth sessions. No direct database access, no separate auth system, no new domain logic.

### Project Structure

```
malt-radar/
├── frontend/                  # Existing — Flutter mobile + legacy web
│   ├── lib/
│   ├── web/                   # Flutter web output (stays live during migration)
│   └── pubspec.yaml
├── webapp-next/               # NEW — Next.js SSR/SSG web
│   ├── app/
│   │   ├── page.tsx               # Homepage (SSG + ISR)
│   │   ├── w/[id]/page.tsx        # Whisky detail (ISR)
│   │   ├── whiskies/page.tsx      # Listing/search (SSR)
│   │   ├── distillery/page.tsx    # Distillery pages (ISR)
│   │   ├── sitemap.ts             # Dynamic sitemap from FastAPI
│   │   ├── robots.ts              # robots.txt
│   │   ├── layout.tsx             # Root layout + theme provider
│   │   └── not-found.tsx
│   ├── components/
│   │   ├── layout/                # Header, footer, nav
│   │   ├── WhiskyCard.tsx
│   │   ├── FlavorProfileChart.tsx  # Placeholder (Phase 2)
│   │   └── ...
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts           # FastAPI HTTP client
│   │   │   ├── types.ts            # Response types
│   │   │   └── auth.ts             # Auth session interface (contract)
│   │   ├── theme/                  # CSS variables + design tokens
│   │   └── utils/
│   ├── next.config.ts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── backend/                  # Existing — FastAPI, UNCHANGED
│   ├── app/
│   └── run.py
└── deploy/
```

---

## 3. Routing Strategy

Next.js App Router (`app/`) with a hybrid SSG/SSR/ISR strategy. **No `fallback: 'blocking'`** — the App Router handles dynamic routes natively via `revalidate` cache semantics.

| Route | Mode | Revalidation |
|---|---|---|
| `/` | SSG | `revalidate: 3600` (1h) |
| `/w/[id]` | ISR | `revalidate: 86400` (24h) — no build-time pre-generation of all 4.5k pages |
| `/whiskies` | SSR | Per-request (search/filter params) |
| `/distillery/[id]` | ISR | `revalidate: 43200` (12h) |
| `/sitemap.xml` | SSG | Regenerated at each build from FastAPI data |
| `/robots.txt` | SSG | Static |

**Strategy rationale:**
- 4,593 whiskies must NOT all be pre-rendered at build time. That's slow and wasteful.
- ISR with `revalidate` means: first request to `/w/[id]` generates the page server-side, caches it. Subsequent requests hit the cache. After `revalidate` seconds, Next.js regenerates in the background.
- Public/SEO-critical pages that are pre-rendered are the homepage and distilleries (fewer entities).

---

## 4. Data Layer (API Client)

### Client Interface

```typescript
// lib/api/client.ts
export class MaltRadarApi {
  private baseUrl: string;

  // Public catalog (anonymous, allowlist-gated)
  getWhiskies(params: WhiskyListParams): Promise<WhiskyListResponse>
  getWhisky(id: string): Promise<WhiskyDetail>
  search(query: string, filters?: FilterParams): Promise<SearchResult[]>
  getDistilleries(): Promise<Distillery[]>
  getDistillery(id: string): Promise<DistilleryDetail>

  // Phase 2 (deferred — not in Phase 1 client)
  // getFlavorProfile(id: string): Promise<FlavorProfile>
  // getTastingNotes(id: string): Promise<TastingNote[]>
  // getSimilar(id: string, limit?: number): Promise<WhiskySummary[]>
}
```

### API Contract Mapping

| Next.js client | FastAPI endpoint | Auth required? |
|---|---|---|
| `getWhiskies` | `GET /api/db/public/whiskies` | ❌ (anonymous, allowlist) |
| `getWhisky` | `GET /api/db/public/whiskies/{id}` | ❌ |
| `search` | `GET /api/db/public/search?q=...` | ❌ |
| `getDistilleries` | `GET /api/db/public/distilleries` | ❌ |
| `getDistillery` | `GET /api/db/public/distilleries/{id}` | ❌ (if endpoint exists) / falls back to `/api/db/distilleries` |

> **Note:** If FastAPI doesn't yet have `GET /api/db/public/distilleries/{id}`, that's a backend gap to identify. The Next.js client should be written defensively (try public, fall back to authenticated).

---

## 5. Auth Integration (Interface Contract Only)

**Phase 1 does NOT perform any auth fetches.** Auth is defined as a contract for Phase 2 extensibility.

```typescript
// lib/api/auth.ts
export interface AuthState {
  user: User | null;
  isGuest: boolean;
  isLoading: boolean;
}

export async function getAuthUser(request: Request): Promise<AuthState> {
  // Phase 1: not called by any page
  // Phase 2: forwards cookies to FastAPI /auth/verify
  const cookies = request.headers.get('cookie');
  // const res = await fetch(`${API_BASE}/auth/verify`, {
  //   headers: { cookie: cookies || '' }
  // });
  return { user: null, isGuest: true, isLoading: false };
}
```

This interface exists so Phase 2 auth-gated features (user collections, saved whiskies) can be added without restructuring the app. No page in Phase 1 calls `getAuthUser()`.

---

## 6. SEO Features

### Structured Data (JSON-LD)

Each whisky detail page embeds JSON-LD:

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Laphroaig 10 Year Old",
  "description": "...",
  "brand": { "@type": "Brand", "name": "Laphroaig" },
  "category": "Single Malt Scotch Whisky",
  "additionalProperty": [
    { "name": "Region", "value": "Islay" },
    { "name": "ABV", "value": "40" }
  ]
}
```

### Sitemap

`app/sitemap.ts` — dynamically generated at build time by fetching the full public whisky + distillery catalog from FastAPI. All 4,500+ URLs are listed as sitemap entries (URLs only, not pre-rendered HTML).

### Metadata API

Uses Next.js Metadata API for per-route meta tags:

```typescript
// app/w/[id]/page.tsx
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const whisky = await api.getWhisky(params.id);
  return {
    title: `${whisky.name} | ${whisky.brand} | Malt Radar`,
    description: whisky.description,
    openGraph: {
      title: `${whisky.name} | Malt Radar`,
      description: whisky.description,
    },
    alternates: {
      canonical: `https://maltradar.com/w/${whisky.id}`,
      languages: { 'en': `/en/w/${whisky.id}`, 'tr': `/tr/w/${whisky.id}` },
    },
  };
}
```

### robots.txt

Served from `app/robots.ts`:

```
User-agent: *
Allow: /
Sitemap: https://maltradar.com/sitemap.xml
```

### Price Rule

**Price is NEVER rendered in UI or API responses.** The `WhiskyDetail` type explicitly excludes price fields. The FastAPI backend already redacts price at the adapter layer (`ProductionReadAdapter._redact_prices`). Phase 1 client does not request or render price.

---

## 7. Theme / Design System

Transcribe the existing "Modern Cellar" design tokens (`DESIGN.md`) into CSS + Tailwind:

| Token | Hex | Usage |
|---|---|---|
| `caskChar` | `#1A120B` | Background |
| `surface` | `#241A10` | Card ground |
| `surfaceElevated` | `#2B1F14` | Elevated surfaces |
| `copper` | `#A6672C` | Primary accent |
| `verdigris` | `#5C7A6E` | Secondary / badges |
| `brass` | `#C9A227` | Medallion only |
| `oxblood` | `#6B1E23` | Warnings / special badges |
| `parchment` | `#EDE1C8` | Text primary |

**Fonts:** Fraunces (headlines), SourceSerif4 (body), Inter (UI), CourierPrime (medallion/labels). All bundled as static assets — no `google_fonts` runtime fetch (offline-safe, Play Store-safe).

Dark-mode only (matches existing Flutter design).

---

## 8. Phase 1 Scope

### In Scope

- **Homepage** — featured whiskies, intro copy, SEO-first
- **Whisky listing** — SSR with search + chip filters (Bourbon/Single Malt/etc.)
- **Whisky detail** — name, brand, distillery, region, age, ABV, description (NO tasting notes, NO flavor radar, NO price)
- **Distillery pages** — distillery info, list of expressions
- **SEO** — structured data, sitemap, canonical, hreflang, robots.txt, meta tags, OpenGraph
- **Responsive design** — mobile-first, matches existing design system
- **GA4 Consent Mode v2** — bootstrap script ported from Flutter web's `index.html`
- **Basic analytics** — gtag config on page views

### Out of Scope (Phase 2+)

- Flavor Radar visualization (7-axis chart)
- Tasting notes display
- Similarity recommendations ("Benzer Lezzetler")
- User auth-gated features (collections, saved whiskies)
- Age gate (if applicable)
- Price display

### Extensibility Hooks

Components and data structures are designed so Phase 2 features can be added without restructuring:

- `FlavorProfileChart` — placeholder component that accepts `FlavorProfile` data, renders nothing in Phase 1
- API client has `Phase 2 (deferred)` section with method stubs commented out
- Route files have space for additional data fetches

---

## 9. Route Parity (Public/SEO-Critical Only)

Phase 1 targets **public SEO-critical route parity**, NOT 100% feature parity:

| Current Flutter Web Route | Next.js Phase 1 |
|---|---|
| `/` | ✅ `app/page.tsx` (SSG) |
| `/whiskies` | ✅ `app/whiskies/page.tsx` (SSR) |
| `/w/[id]` | ✅ `app/w/[id]/page.tsx` (ISR) |
| `/distillery/[id]` | ✅ `app/distillery/[id]/page.tsx` (ISR) |
| Tasting notes tab | ❌ Deferred (Phase 2) |
| Flavor radar | ❌ Deferred (Phase 2) |
| Similarity | ❌ Deferred (Phase 2) |
| Auth-gated pages | ❌ Deferred (Phase 2) |

---

## 10. Migration & Cutover

### Phase A: Parallel Development

- `webapp-next/` built alongside `frontend/`
- Deployed to `preview.maltradar.com` (or staging path)
- Consumes same FastAPI backend

### Phase B: Staging Verification

- **Route parity check** — all SEO-critical public URLs resolve
- **SEO comparison** — sitemap URLs, structured data, meta tags validated
- **Performance** — Lighthouse score, TTFB, bundle size target
- **Visual diff** — design system parity check against Flutter web

### Phase C: Production Cutover

```
maltradar.com
  ↓ (DNS/Cloudflare)
Next.js deployment
  ↓ (HTTPS/API)
FastAPI backend (unchanged)
  ↓
production.db
```

**Rollback:** Single DNS flip back to Flutter web deployment. Backend is never touched.

**Legacy Flutter Web:** Demoted to `legacy.maltradar.com` during transition; removed after 1 release cycle.

---

## 11. Non-Goals

- No backend changes (FastAPI stays as-is)
- No mobile app changes (Flutter mobile unaffected)
- No DB-layer changes (no direct SQLite access from Next.js)
- No auth system rewrite (FastAPI auth contract is source of truth)
- No 100% feature parity in Phase 1

---

## 12. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Flutter web + Next.js in same repo = build complexity | Separate `package.json` + CI paths; independent build jobs |
| SEO regression on some routes | Pre-cutover SEO audit via Lighthouse + manual spot-check |
| API contract mismatch between web and mobile | Web uses same public API as mobile; contract is shared |
| Bundle size too large | Tailwind with `purgeCSS` content scanning; tree-shaking enforced |
| ISR stale data for popular whiskies | Configurable `revalidate` per route type |

---

## 13. Open Questions

1. **Does FastAPI have `GET /api/db/public/distilleries/{id}`?** If not, this is a backend gap — either add the endpoint or Next.js falls back to the authenticated `/api/db/distilleries/{id}`.
2. **Preview deployment target** — Vercel (native Next.js) vs. same FastAPI host? Affects `next.config.ts` and deployment scripts.
3. **Build-time data fetching** — homepage "featured whiskies" needs a curated list. Is there an existing FastAPI endpoint for this, or do we hardcode a top-N?
