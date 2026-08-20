import { MaltRadarApi } from '@/lib/api/client';
import type { DistillerySummary } from '@/lib/api/types';
import Link from 'next/link';

const api = new MaltRadarApi();

export const revalidate = 43200; // ISR: 12 hours

interface Props {
  searchParams: Promise<{ page?: string }>;
}

export const metadata = {
  title: 'Distilleries | Malt Radar',
  description: 'Browse whisky distilleries in the Malt Radar database — names and expression counts.',
  alternates: { canonical: 'https://maltradar.com/distilleries' },
};

const PAGE_SIZE = 50; // backend clamps limit to 50 (verified 2026-08-18)

export default async function DistilleriesPage({ searchParams }: Props) {
  const sp = await searchParams;
  const pageNum = Math.max(1, parseInt(sp.page ?? '1', 10) || 1);
  const offset = (pageNum - 1) * PAGE_SIZE;

  const data = await api.getDistilleries(PAGE_SIZE, offset).catch(() => ({
    items: [] as DistillerySummary[],
    total_count: 0,
    limit: PAGE_SIZE,
    offset,
  }));

  // NOTE: total_count is page-length, not corpus total (verified 2026-08-18).
  const hasNext = data.items.length === PAGE_SIZE;
  const distilleries = [...data.items].sort((a, b) => a.name.localeCompare(b.name));

  return (
    <article className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-fraunces font-semibold text-parchment mb-2">Distilleries</h1>
      <p className="text-textSecondary mb-8">Page {pageNum}{hasNext ? ' • More →' : ''}</p>
      <p className="text-sm text-textMuted mb-4">Showing {data.items.length} distilleries (alphabetical; {hasNext ? 'more available' : 'end of list'})</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {distilleries.map((d) => (
          <div key={d.distillery_id} className="bg-surfaceElevated rounded-xl p-4 border border-white/10">
            <h2 className="text-parchment font-semibold">{d.name}</h2>
            <p className="text-sm text-textMuted mt-1">{d.whisky_count} expressions</p>
          </div>
        ))}
      </div>

      {data.items.length === 0 && (
        <p className="text-textMuted">No distilleries found.</p>
      )}

      {/* Pagination — server-rendered links, no client JS (short-page detection) */}
      <nav className="flex items-center justify-between mt-10" aria-label="Pagination">
        {pageNum > 1 ? (
          <Link href={`/distilleries?page=${pageNum - 1}`} className="text-copper hover:underline">
            ← Previous
          </Link>
        ) : <span />}
        <span className="text-sm text-textMuted">Page {pageNum}{hasNext ? ' • More →' : ''}</span>
        {hasNext ? (
          <Link href={`/distilleries?page=${pageNum + 1}`} className="text-copper hover:underline">
            Next →
          </Link>
        ) : <span />}
      </nav>
    </article>
  );
}
