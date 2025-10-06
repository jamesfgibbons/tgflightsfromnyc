import './globals.css';
import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'VibeNet • Flight Deal Symphony (Vercel Concepts)',
  description: 'Split‑flap, Radio Tuner, and Deal Composer concepts powered by VibeNet + FastAPI',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="wrap">
            <Link className="brand" href="/">VibeNet</Link>
            <nav>
              <Link href="/embed">Split‑Flap</Link>
              <Link href="/radio">Radio Tuner</Link>
              <Link href="/composer">Deal Composer</Link>
            </nav>
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="site-footer"><span>© VibeNet Concepts on Vercel</span></footer>
      </body>
    </html>
  );
}

