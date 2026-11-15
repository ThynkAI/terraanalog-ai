"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { NAV } from "@/lib/constants";
import { MetaProvider, useMeta } from "./MetaContext";
import { DataStatusBadge } from "./ui";

function Logo() {
  return (
    <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="12" cy="16" r="9" fill="#1f4e79" stroke="#67d4ee" strokeWidth="1.2" />
      <path d="M5 14c3-2 6 1 9-1s3-4 6-3" stroke="#4ade80" strokeWidth="1.4" fill="none" />
      <circle cx="25" cy="8" r="3.4" fill="#c9ced6" />
      <circle cx="25.5" cy="24" r="3" fill="#e8743b" />
      <path d="M19 12 L23 9.5 M19 20 L23 22.5" stroke="#8b94a5" strokeWidth="0.8" strokeDasharray="1.5 1.5" />
    </svg>
  );
}

function Header() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [pathname]);
  return (
    <header className="no-print sticky top-0 z-40 border-b border-white/[0.07] bg-space-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] items-center gap-3 px-4 py-2.5">
        <Link href="/" className="flex shrink-0 items-center gap-2" aria-label="TerraAnalog AI home">
          <Logo />
          <span className="leading-tight">
            <span className="block text-[15px] font-semibold tracking-tight text-lunar-50">
              TerraAnalog <span className="text-mars-400">AI</span>
            </span>
            <span className="hidden text-[10px] uppercase tracking-[0.18em] text-lunar-400 sm:block">Earth as a testbed for Moon &amp; Mars</span>
          </span>
        </Link>
        <nav aria-label="Main" className="ml-4 hidden flex-1 xl:block">
          <ul className="flex flex-wrap items-center gap-0.5">
            {NAV.map((n) => {
              const active = n.href === "/" ? pathname === "/" : pathname.startsWith(n.href);
              return (
                <li key={n.href}>
                  <Link
                    href={n.href}
                    aria-current={active ? "page" : undefined}
                    className={`rounded-md px-2.5 py-1.5 text-[13px] transition ${active ? "bg-white/10 text-white" : "text-lunar-300 hover:bg-white/5 hover:text-white"}`}
                  >
                    {n.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <DataStatusBadge />
          <button
            className="btn xl:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((o) => !o)}
          >
            <span aria-hidden="true">☰</span>
            <span>Menu</span>
          </button>
        </div>
      </div>
      {open && (
        <nav id="mobile-nav" aria-label="Main mobile" className="border-t border-white/10 bg-space-900 xl:hidden">
          <ul className="mx-auto grid max-w-[1600px] grid-cols-1 gap-1 p-3 sm:grid-cols-2">
            {NAV.map((n) => (
              <li key={n.href}>
                <Link href={n.href} className="block rounded-md px-3 py-2 text-sm text-lunar-100 hover:bg-white/5" aria-current={pathname === n.href ? "page" : undefined}>
                  {n.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </header>
  );
}

function SyntheticBanner() {
  const { meta } = useMeta();
  if (!meta?.data_status.synthetic) return null;
  return (
    <div role="note" className="no-print border-b border-pink-400/20 bg-pink-500/[0.07] px-4 py-1.5 text-center text-xs text-pink-200">
      <strong className="font-semibold">Synthetic fixture data.</strong> Scores are synthetic or provisional placeholders, not measurements. Planetary reference
      coordinates are real (IAU/USGS Gazetteer). <Link href="/data" className="underline underline-offset-2">Provenance details</Link>
    </div>
  );
}

function ResearchNotice() {
  const { meta } = useMeta();
  if (!meta || meta.data_status.synthetic || !meta.notice) return null;
  return (
    <div role="note" data-testid="research-notice" className="no-print border-b border-emerald-400/15 bg-emerald-500/[0.05] px-4 py-1.5 text-center text-xs text-emerald-100/90">
      <strong className="font-semibold">Research dataset.</strong> {meta.notice} <Link href="/data" className="underline underline-offset-2">Provenance details</Link>
    </div>
  );
}

function ServiceError() {
  const { error, retry, loading } = useMeta();
  if (!error) return null;
  return (
    <div role="alert" className="border-b border-red-400/30 bg-red-500/10 px-4 py-2 text-center text-sm text-red-200">
      <span>The research service is temporarily unavailable. It may be waking from inactivity.</span>{" "}
      <button className="underline underline-offset-2 disabled:opacity-50" onClick={retry} disabled={loading}>{loading ? "Reconnecting…" : "Retry connection"}</button>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <MetaProvider>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-mars-600 focus:px-3 focus:py-2 focus:text-white">
        Skip to content
      </a>
      <Header />
      <SyntheticBanner />
      <ResearchNotice />
      <ServiceError />
      <main id="main" className="mx-auto max-w-[1600px] px-4 pb-16 pt-5">
        {children}
      </main>
      <footer className="no-print border-t border-white/[0.06] px-4 py-6 text-center text-xs text-lunar-400">
        TerraAnalog AI · Built for NASA Space Apps · Not affiliated with or endorsed by NASA. Planetary imagery: NASA Moon Trek / Mars Trek · Earth tiles: NASA GIBS · Land: Natural Earth.
        Analog scores are decision-support proxies, not landing-site selections.
      </footer>
    </MetaProvider>
  );
}
