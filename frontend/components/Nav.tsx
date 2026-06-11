"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Tournament", icon: "\u{1F3C6}" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <>
      {/* Desktop top nav */}
      <nav className="hidden md:block border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 flex items-center h-14 gap-1">
          <span className="text-lg font-bold text-emerald-400 mr-6">
            WC2026
          </span>
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                pathname === link.href
                  ? "bg-zinc-800 text-emerald-400"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900"
              }`}
            >
              {link.icon} {link.label}
            </Link>
          ))}
        </div>
      </nav>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 border-t border-zinc-800 bg-zinc-950/95 backdrop-blur-sm z-40">
        <div className="flex justify-around items-center h-16">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 ${
                pathname === link.href ? "text-emerald-400" : "text-zinc-500"
              }`}
            >
              <span className="text-xl">{link.icon}</span>
              <span className="text-[10px] font-medium">{link.label}</span>
            </Link>
          ))}
        </div>
      </nav>
    </>
  );
}
