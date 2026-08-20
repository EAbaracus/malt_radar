import Link from 'next/link';
export function Header() {
  return (
    <header className="flex justify-between items-center px-5 py-4 border-b border-white/10">
      <Link href="/" className="text-2xl font-fraunces font-semibold text-copper">Malt Radar</Link>
      <nav className="flex gap-6">
        <Link href="/whiskies" className="text-sm text-textSecondary hover:text-copper transition-colors">Whiskies</Link>
        <Link href="/distilleries" className="text-sm text-textSecondary hover:text-copper transition-colors">Distilleries</Link>
      </nav>
    </header>
  );
}