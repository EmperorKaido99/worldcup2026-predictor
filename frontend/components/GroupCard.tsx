"use client";

import { useState } from "react";
import TeamBadge from "./TeamBadge";
import {
  Group,
  GroupStanding,
  getGroupMatches,
  computeStandings,
  estimateGoals,
} from "@/lib/wc2026";
import { predictMatch } from "@/lib/api";

interface GroupCardProps {
  group: Group;
  standings: GroupStanding[] | null;
  onStandingsUpdate: (groupName: string, standings: GroupStanding[]) => void;
}

export default function GroupCard({
  group,
  standings,
  onStandingsUpdate,
}: GroupCardProps) {
  const [simulating, setSimulating] = useState(false);

  async function simulateGroup() {
    setSimulating(true);
    try {
      const matches = getGroupMatches(group);
      const results: Record<string, { homeGoals: number; awayGoals: number }> =
        {};

      for (const match of matches) {
        const pred = await predictMatch({
          home: match.home.id,
          away: match.away.id,
          neutral: true,
        });
        const goals = estimateGoals(pred.probabilities);
        results[`${match.home.id}-${match.away.id}`] = goals;
      }

      const newStandings = computeStandings(group, results);
      onStandingsUpdate(group.name, newStandings);
    } catch {
      // silently fail — user can retry
    } finally {
      setSimulating(false);
    }
  }

  return (
    <div className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <h3 className="font-bold text-lg">
          Group <span className="text-emerald-400">{group.name}</span>
        </h3>
        <button
          onClick={simulateGroup}
          disabled={simulating}
          className="text-xs px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white transition-colors disabled:opacity-50"
        >
          {simulating ? "Simulating..." : standings ? "Re-simulate" : "Simulate"}
        </button>
      </div>

      {standings ? (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-zinc-500 text-xs">
              <th className="text-left px-4 py-2">Team</th>
              <th className="w-8 text-center">P</th>
              <th className="w-8 text-center">W</th>
              <th className="w-8 text-center">D</th>
              <th className="w-8 text-center">L</th>
              <th className="w-10 text-center">GD</th>
              <th className="w-10 text-center pr-4 font-bold text-zinc-400">Pts</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((s, i) => {
              const rowColor =
                i < 2
                  ? "bg-emerald-950/30 border-l-2 border-l-emerald-500"
                  : i === 2
                    ? "bg-amber-950/20 border-l-2 border-l-amber-500"
                    : "border-l-2 border-l-transparent opacity-60";
              return (
                <tr key={s.teamId} className={rowColor}>
                  <td className="px-4 py-2">
                    <TeamBadge teamId={s.teamId} teamName={s.teamName} size="sm" />
                  </td>
                  <td className="text-center text-zinc-400">{s.played}</td>
                  <td className="text-center text-zinc-400">{s.won}</td>
                  <td className="text-center text-zinc-400">{s.drawn}</td>
                  <td className="text-center text-zinc-400">{s.lost}</td>
                  <td className="text-center text-zinc-400">
                    {s.gd > 0 ? `+${s.gd}` : s.gd}
                  </td>
                  <td className="text-center pr-4 font-bold">{s.points}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <div className="px-4 py-3 space-y-2">
          {group.teams.map((t) => (
            <div key={t.id} className="flex items-center gap-2 py-1">
              <TeamBadge teamId={t.id} teamName={t.name} size="sm" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
