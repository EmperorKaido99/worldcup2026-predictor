"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Tournament", icon: "\u{1F3C6}" },
  { href: "/elimination", label: "Elimination", icon: "\u{26A0}\u{FE0F}" },
  { href: "/xg", label: "xG", icon: "\u{26BD}" },
  { href: "/penalties", label: "Penalties", icon: "\u{1F945}" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <>
      {/* Desktop top nav */}
      <nav className="hidden md:block border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 flex items-center h-14 gap-1">
          <Link href="/" className="flex items-center gap-2 mr-6 group">
            <span className="text-lg font-bold bg-gradient-to-r from-emerald-400 to-emerald-300 bg-clip-text text-transparent group-hover:from-emerald-300 group-hover:to-emerald-200 transition-all">
              WC2026
            </span>
            <span className="text-[10px] text-zinc-600 font-medium uppercase tracking-widest">
              Predictor
            </span>
          </Link>
          <div className="flex items-center gap-0.5">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  pathname === link.href
                    ? "bg-emerald-600/20 text-emerald-400 shadow-sm"
                    : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
                }`}
              >
                <span className="mr-1.5">{link.icon}</span>
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </nav>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 border-t border-zinc-800 bg-zinc-950/95 backdrop-blur-md z-40 safe-area-pb">
        <div className="flex justify-around items-center h-16 px-2">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl transition-all ${
                pathname === link.href
                  ? "text-emerald-400 bg-emerald-500/10"
                  : "text-zinc-500 active:bg-zinc-800"
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
