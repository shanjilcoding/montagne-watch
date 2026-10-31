"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BellRinging, ChartLineUp, ClockCounterClockwise, SquaresFour } from "@phosphor-icons/react";


const links = [
  { href: "/", label: "Overview", icon: ChartLineUp },
  { href: "/catalog", label: "Catalog", icon: SquaresFour },
  { href: "/events", label: "Events", icon: ClockCounterClockwise },
];

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="site-header">
      <div className="header-inner">
        <Link className="brand" href="/" aria-label="Montagne Watch home">
          <span className="brand-mark"><BellRinging size={20} weight="bold" /></span>
          <span>Montagne Watch</span>
        </Link>
        <nav className="primary-nav" aria-label="Primary navigation">
          {links.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === href : pathname.startsWith(href);
            return (
              <Link key={href} className={active ? "nav-link active" : "nav-link"} href={href}>
                <Icon size={18} aria-hidden="true" />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
