import { MaltRadarApi } from '@/lib/api/client';
import type { WhiskySummary } from '@/lib/api/types';
import type { MetadataRoute } from 'next';

const api = new MaltRadarApi();
const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://maltradar.com';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Fetch all whiskies from FastAPI
  // VERIFIED 2026-08-18: backend CLAMPS limit to max 50 (min(max(1,limit),50)).
  // MUST paginate in a loop of 50; a single limit:1000 call returns only 50 rows.
  const whiskies: WhiskySummary[] = [];
  const PAGE = 50;
  for (let offset = 0; ; offset += PAGE) {
    const page = await api.getWhiskies({ limit: PAGE, offset }).catch(() => null);
    if (!page) break;
    whiskies.push(...page.items);
    // FIX: total_count is page-length, not corpus total. Rely on items.length < PAGE
    // as the primary stop condition (backend returns <PAGE on last page).
    if (page.items.length === 0 || page.items.length < PAGE) break;
  }

  // Distillery INDEX URL (static page; details deferred to Phase 2)
  const distilleryUrls: MetadataRoute.Sitemap = [
    {
      url: `${baseUrl}/distilleries`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.6,
    },
  ];

  const whiskyUrls: MetadataRoute.Sitemap = whiskies.map((w) => ({
    url: `${baseUrl}/w/${w.whisky_id}`,
    lastModified: new Date(),
    changeFrequency: 'daily',
    priority: 0.8,
  }));

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'hourly',
      priority: 1,
    },
    {
      url: `${baseUrl}/whiskies`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.8,
    },
    ...whiskyUrls,
    ...distilleryUrls,
  ];
}
