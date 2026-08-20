import { MaltRadarApi } from '@/lib/api/client';
import { SearchBar } from '@/components/SearchBar';
import { FilterChips } from '@/components/FilterChips';
import { WhiskyGrid } from '@/components/WhiskyGrid';
import type { WhiskyListParams } from '@/lib/api/types';

const api = new MaltRadarApi();

interface Props {
  searchParams: Promise<{ q?: string; filter?: string; p?: string }>;
}

export default async function WhiskiesPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = params.q ?? '';
  const filter = params.filter ?? '';
  const page = parseInt(params.p ?? '1', 10);
  const limit = 50;
  const offset = (page - 1) * limit;

  const whiskyParams: WhiskyListParams = {
    limit,
    offset,
  };
  if (query) whiskyParams.q = query;
  if (filter) whiskyParams.filter = filter;

  const result = await api.getWhiskies(whiskyParams);
  const hasNext = result.items.length === limit;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold text-parchment">Whiskies</h1>
      <SearchBar />
      <FilterChips />
      {result.items.length === 0 ? (
        <p className="text-textSecondary">No whiskies found</p>
      ) : (
        <WhiskyGrid
          whiskies={result.items}
          currentPage={page}
          hasNext={hasNext}
          currentQuery={query}
          currentFilter={filter}
        />
      )}
    </div>
  );
}
