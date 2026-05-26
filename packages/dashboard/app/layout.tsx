import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "mnemos dashboard",
  description: "Read-only views over the mnemos agent memory system.",
};

const NAV = [
  { href: "/", label: "home" },
  { href: "/memories", label: "memories" },
  { href: "/eval", label: "eval" },
  { href: "/timeline", label: "timeline" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-(--border) px-6 py-4 flex items-center justify-between">
            <Link href="/" className="text-lg font-bold tracking-tight">
              <span className="text-(--accent)">mnemos</span>{" "}
              <span className="text-(--muted)">/ dashboard</span>
            </Link>
            <nav className="flex gap-6 text-sm">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="hover:text-(--accent) text-(--muted)"
                >
                  {n.label}
                </Link>
              ))}
            </nav>
          </header>
          <main className="px-6 py-8 max-w-6xl mx-auto">{children}</main>
          <footer className="border-t border-(--border) px-6 py-4 text-xs text-(--muted)">
            agent memory system &middot; read-only views &middot; data from{" "}
            <code>http://service:8000</code> and mounted <code>leaderboard.md</code>
          </footer>
        </div>
      </body>
    </html>
  );
}
