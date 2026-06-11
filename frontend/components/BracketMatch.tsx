"use client";

import TeamBadge from "./TeamBadge";

interface BracketMatchProps {
  team1?: string;
  team2?: string;
  team1Name?: string;
  team2Name?: string;
  winner?: string;
  onClick?: () => void;
  compact?: boolean;
}

export default function BracketMatch({
  team1,
  team2,
  team1Name,
  team2Name,
  winner,
  onClick,
  compact = false,
}: BracketMatchProps) {
  const ready = !!team1 && !!team2 && !winner;
  const decided = !!winner;

  return (
    <button
      onClick={ready ? onClick : undefined}
      disabled={!ready}
      className={`w-full rounded-lg border text-left transition-all ${
        decided
          ? "border-emerald-700/50 bg-zinc-900/80"
          : ready
            ? "border-zinc-700 bg-zinc-900 hover:border-emerald-500 hover:bg-zinc-800 cursor-pointer"
            : "border-zinc-800 bg-zinc-950/50 opacity-50 cursor-default"
      } ${compact ? "p-1.5" : "p-2"}`}
    >
      <div className={`space-y-0.5 ${compact ? "text-xs" : "text-sm"}`}>
        <div
          className={`flex items-center gap-1.5 px-1 py-0.5 rounded ${
            winner === team1
              ? "bg-emerald-600/20 text-emerald-400 font-medium"
              : winner && winner !== team1
                ? "opacity-40"
                : ""
          }`}
        >
          {team1 ? (
            <TeamBadge
              teamId={team1}
              teamName={team1Name || team1}
              size="sm"
            />
          ) : (
            <span className="text-zinc-600 italic">TBD</span>
          )}
        </div>
        <div className="border-t border-zinc-800" />
        <div
          className={`flex items-center gap-1.5 px-1 py-0.5 rounded ${
            winner === team2
              ? "bg-emerald-600/20 text-emerald-400 font-medium"
              : winner && winner !== team2
                ? "opacity-40"
                : ""
          }`}
        >
          {team2 ? (
            <TeamBadge
              teamId={team2}
              teamName={team2Name || team2}
              size="sm"
            />
          ) : (
            <span className="text-zinc-600 italic">TBD</span>
          )}
        </div>
      </div>
    </button>
  );
}
