"use client";

import { useState, useRef, useEffect } from "react";
import { Team } from "@/lib/api";
import { getFlag } from "@/lib/flags";

interface TeamSelectProps {
  teams: Team[];
  value: string;
  onChange: (id: string) => void;
  label: string;
  placeholder?: string;
}

export default function TeamSelect({
  teams,
  value,
  onChange,
  label,
  placeholder = "Select team...",
}: TeamSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const selected = teams.find((t) => t.id === value);
  const filtered = teams.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div ref={ref} className="relative w-full">
      <label className="block text-sm font-medium text-zinc-400 mb-1.5">
        {label}
      </label>
      <button
        type="button"
        onClick={() => {
          setOpen(!open);
          setSearch("");
        }}
        className="w-full flex items-center gap-2 px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-xl text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 transition-colors hover:border-zinc-500"
      >
        {selected ? (
          <>
            <span className="text-xl">{getFlag(selected.id)}</span>
            <span className="text-white">{selected.name}</span>
          </>
        ) : (
          <span className="text-zinc-500">{placeholder}</span>
        )}
        <svg
          className="ml-auto w-4 h-4 text-zinc-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-zinc-900 border border-zinc-700 rounded-xl shadow-xl max-h-64 overflow-hidden">
          <div className="p-2">
            <input
              autoFocus
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search..."
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-white text-sm placeholder-zinc-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
            />
          </div>
          <ul className="max-h-48 overflow-y-auto">
            {filtered.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => {
                    onChange(t.id);
                    setOpen(false);
                    setSearch("");
                  }}
                  className={`w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-zinc-800 transition-colors ${
                    t.id === value ? "bg-zinc-800 text-emerald-400" : "text-white"
                  }`}
                >
                  <span className="text-lg">{getFlag(t.id)}</span>
                  <span className="text-sm">{t.name}</span>
                </button>
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="px-4 py-3 text-sm text-zinc-500">No teams found</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
