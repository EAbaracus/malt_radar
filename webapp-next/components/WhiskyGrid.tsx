import Link from 'next/link';
import type { WhiskySummary } from '@/lib/api/types';

interface Props {
  whiskies: WhiskySummary[];
  currentPage: number;
  hasNext: boolean;
  currentQuery: string;
  currentFilter: string;
}

export function WhiskyGrid({
  whiskies,
  currentPage,
  hasNext,
  currentQuery,
  currentFilter,
}: Props) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {whiskies.map((whisky) => (
          <Link
            key={whisky.whisky_id}
            href={`/w/${whisky.whisky_id}`}
            className="block bg-surface border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-border"
          >
            <div className="p-4">
              <h3 className="mb-2 text-lg font-bold text-parchment">{whisky.name}</h3>
              <p className="mb-1 text-textSecondary">{whisky.brand}</p>
              <p className="mb-1 text-textSecondary">{whisky.region}</p>
              <p className="text-textSecondary">{whisky.abv}% ABV</p>
            </div>
          </Link>
        ))}
      </div>

      <div className="flex justify-between items-center mt-6">
        {currentPage > 1 && (
          <Link
            href={
              (() => {
                const params = new URLSearchParams();
                if (currentQuery) params.set('q', currentQuery);
                if (currentFilter) params.set('filter', currentFilter);
                params.set('p', (currentPage - 1).toString());
                return `/whiskies?${params.toString()}`;
              })()
            }
            className="text-textSecondary hover:text-parchment"
          >
            Prev
          </Link>
        )}
        {hasNext && (
          <Link
            href={
              (() => {
                const params = new URLSearchParams();
                if (currentQuery) params.set('q', currentQuery);
                if (currentFilter) params.set('filter', currentFilter);
                params.set('p', (currentPage + 1).toString());
                return `/whiskies?${params.toString()}`;
              })()
            }
            className="text-textSecondary hover:text-parchment"
          >
            Next
          </Link>
        )}
      </div>
    </div>
  );
}