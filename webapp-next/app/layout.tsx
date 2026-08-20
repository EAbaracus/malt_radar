import type { ReactNode } from 'react';
import '../styles/globals.css';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
export const metadata = {
  title: 'Malt Radar — Whisky Flavor Database',
  description: 'Whisky flavor profiles, read from data. 4,700+ whiskies, distilleries and regions — with sourced evidence.',
  icons: { icon: '/favicon.png' },
};
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="bg-surface text-parchment">
      <body className="font-body min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 container mx-auto px-5 py-8">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}