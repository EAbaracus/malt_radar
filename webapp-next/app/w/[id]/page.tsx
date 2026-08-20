import { notFound } from 'next/navigation';
import { MaltRadarApi } from '@/lib/api/client';
import { FlavorProfileChart } from '@/components/FlavorProfileChart';
import type { WhiskyDetail } from '@/lib/api/types';
import type { Metadata } from 'next';

const api = new MaltRadarApi();

export const revalidate = 86400; // ISR: 24 hours

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const whisky = await api.getWhisky(id);

  if (!whisky) {
    return { title: 'Whisky Not Found | Malt Radar' };
  }

  return {
    title: `${whisky.name} — ${whisky.brand || whisky.distillery_name || ''} | Malt Radar`,
    description: `${whisky.name} — ${whisky.region || 'whisky'} flavor profile.`,
    openGraph: {
      title: `${whisky.name} | Malt Radar`,
      description: `${whisky.name} — ${whisky.region || 'whisky'} flavor profile.`,
    },
    alternates: {
      canonical: `https://maltradar.com/w/${whisky.whisky_id}`,
    },
  };
}

export default async function WhiskyPage({ params }: Props) {
  const { id } = await params;
  const whisky = await api.getWhisky(id);

  if (!whisky) {
    notFound();
  }

  const profile = await api.getFlavorProfile(id).catch(() => null);

  return (
    <article className="max-w-4xl mx-auto">
      <div className="bg-surfaceElevated rounded-xl p-8 border border-white/10">
        <h1 className="text-3xl font-fraunces font-semibold text-parchment mb-2">
          {whisky.name}
        </h1>

        {whisky.brand && (
          <p className="text-textSecondary mb-1">{whisky.brand}</p>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 text-sm">
          {whisky.region && (
            <div>
              <span className="text-textMuted">Region</span>
              <p className="text-parchment">{whisky.region}</p>
            </div>
          )}
          {whisky.type && (
            <div>
              <span className="text-textMuted">Type</span>
              <p className="text-parchment">{whisky.type}</p>
            </div>
          )}
          {whisky.age && (
            <div>
              <span className="text-textMuted">Age</span>
              <p className="text-parchment">{whisky.age}</p>
            </div>
          )}
          {whisky.abv != null && (
            <div>
              <span className="text-textMuted">ABV</span>
              <p className="text-parchment">{whisky.abv}%</p>
            </div>
          )}
        </div>

        {whisky.original_name && whisky.original_name !== whisky.name && (
          <p className="text-textSecondary text-sm mt-4">
            Also known as: {whisky.original_name}
          </p>
        )}

        <div className="mt-8">
          <FlavorProfileChart profile={profile} />
        </div>
      </div>
    </article>
  );
}
