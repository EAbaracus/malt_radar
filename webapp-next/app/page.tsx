import Link from 'next/link';
import { MaltRadarApi } from '@/lib/api/client';
import type { WhiskySummary, DistillerySummary } from '@/lib/api/types';
const api = new MaltRadarApi();
export const revalidate = 3600;
export default async function HomePage() {
  const [whiskies, distilleries] = await Promise.all([
    api.getWhiskies({ limit: 12 }),
    api.getDistilleries(12, 0),  // POSITIONAL args, NOT object — matches T3 client
  ]).catch(() => [{ items: [] }, { items: [] }]);
  return (
    <div className="space-y-12">
      <section>
        <h1 className="text-4xl font-fraunces font-semibold text-parchment mb-4">Malt Radar</h1>
        <p className="text-textSecondary max-w-2xl">Whisky flavor profiles, read from data. 4,700+ whiskies, distilleries and regions — with sourced evidence.</p>
      </section>
      <section>
        <h2 className="text-xl font-fraunces text-parchment mb-6">Featured Whiskies</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {whiskies.items.map((w: WhiskySummary) => (<WhiskyCard key={w.whisky_id} whisky={w} />))}
        </div>
      </section>
      <section>
        <h2 className="text-xl font-fraunces text-parchment mb-6">Distilleries</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {distilleries.items.map((d: DistillerySummary) => (<DistilleryCard key={d.distillery_id} distillery={d} />))}
        </div>
      </section>
    </div>
  );
}
function WhiskyCard({ whisky }: { whisky: WhiskySummary }) {
  return (
    <Link href={`/w/${whisky.whisky_id}`} className="group block">
      <div className="bg-surfaceElevated rounded-xl p-4 border border-white/10 group-hover:border-copper/40 transition-colors">
        <h3 className="text-parchment font-semibold group-hover:text-copper transition-colors">{whisky.name}</h3>
        {whisky.brand && (<p className="text-sm text-textSecondary mt-1">{whisky.brand}</p>)}
        {whisky.region && (<p className="text-xs text-textMuted mt-1">{whisky.region}</p>)}
      </div>
    </Link>
  );
}
function DistilleryCard({ distillery }: { distillery: DistillerySummary }) {
  return (
    <div className="bg-surfaceElevated rounded-xl p-4 border border-white/10">
      <h3 className="text-parchment font-semibold">{distillery.name}</h3>
      <p className="text-sm text-textSecondary mt-1">{distillery.whisky_count} expressions</p>
    </div>
  );
}