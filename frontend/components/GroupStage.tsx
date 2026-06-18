"use client";

import GroupCard, { LiveMatchResult } from "./GroupCard";
import { GROUPS, GroupStanding } from "@/lib/wc2026";

interface MatchResult {
  homeGoals: number;
  awayGoals: number;
  probs: { home_win: number; draw: number; away_win: number };
}

interface GroupStageProps {
  standings: Record<string, GroupStanding[]>;
  matchResults: Record<string, Record<string, MatchResult>>;
  liveResults?: Record<string, Record<string, LiveMatchResult>>;
  onStandingsUpdate: (groupName: string, standings: GroupStanding[]) => void;
  onMatchResultsUpdate: (groupName: string, results: Record<string, MatchResult>) => void;
  onSimulateAll: () => void;
  simulatingAll: boolean;
  simulationProgress: number;
}

export default function GroupStage({
  standings,
  matchResults,
  liveResults = {},
  onStandingsUpdate,
  onMatchResultsUpdate,
  onSimulateAll,
  simulatingAll,
  simulationProgress,
}: GroupStageProps) {
  const completedGroups = Object.keys(standings).length;
  const allGroupsSimulated = completedGroups === 12;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-zinc-400">
          <span className="font-bold text-white">{completedGroups}</span>/12 groups completed
        </div>
        <button
          onClick={onSimulateAll}
          disabled={simulatingAll}
          className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-600/20 hover:shadow-emerald-500/30"
        >
          {simulatingAll
            ? `Simulating... ${simulationProgress}/72`
            : allGroupsSimulated
              ? "Re-simulate All"
              : "Simulate All Groups"}
        </button>
      </div>

      {simulatingAll && (
        <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
          <div
            className="bg-gradient-to-r from-emerald-500 to-emerald-400 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(simulationProgress / 72) * 100}%` }}
          />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {GROUPS.map((group) => (
          <GroupCard
            key={group.name}
            group={group}
            standings={standings[group.name] || null}
            matchResults={matchResults[group.name] || {}}
            liveResults={liveResults[group.name] || {}}
            onStandingsUpdate={onStandingsUpdate}
            onMatchResultsUpdate={onMatchResultsUpdate}
          />
        ))}
      </div>
    </div>
  );
}
