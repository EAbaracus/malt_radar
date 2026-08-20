'use client';

import { useRouter, useSearchParams } from 'next/navigation';

const CHIPS = [
  'single malt',
  'blended',
  'bourbon',
  'speyside',
  'islay',
  'highland',
  'peated',
  'smoky',
  'sherry',
];

export function FilterChips() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeFilter = searchParams.get('filter') || '';

  const toggleChip = (chip: string) => {
    const params = new URLSearchParams(searchParams.toString());
    const currentFilters = activeFilter.split(',').filter(Boolean);
    const index = currentFilters.indexOf(chip);
    let newFilters: string[];
    if (index === -1) {
      newFilters = [...currentFilters, chip];
    } else {
      newFilters = [...currentFilters.slice(0, index), ...currentFilters.slice(index + 1)];
    }
    params.set('filter', newFilters.join(','));
    // preserve q param (already in searchParams)
    const url = `${window.location.pathname}?${params.toString()}`;
    router.replace(url, { scroll: false });
  };

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {CHIPS.map((chip) => {
        const isActive = activeFilter.split(',').includes(chip);
        return (
          <button
            key={chip}
            onClick={() => toggleChip(chip)}
            className={`${isActive
              ? 'bg-copper text-cask font-semibold'
              : 'bg-white/5 text-textSecondary hover:bg-white/10'}
              rounded-full px-3 py-1 text-xs`}
          >
            {chip}
          </button>
        );
      })}
    </div>
  );
}