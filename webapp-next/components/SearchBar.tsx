'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export function SearchBar() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');

  useEffect(() => {
    const handler = setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString());
      if (query) {
        params.set('q', query);
      } else {
        params.delete('q');
      }
      const url = `${window.location.pathname}?${params.toString()}`;
      router.replace(url, { scroll: false });
    }, 300);

    return () => clearTimeout(handler);
  }, [query, searchParams, router]);

  return (
    <div className="relative mb-6">
      <input
        type="text"
        placeholder="Search whiskies..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full bg-surface border border-white/10 rounded-lg px-4 py-2 text-parchment placeholder-textMuted focus:outline-none focus:border-copper"
        minLength={2}
      />
    </div>
  );
}