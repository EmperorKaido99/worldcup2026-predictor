"use client";

import GroupCard from "./GroupCard";
import { GROUPS, GroupStanding } from "@/lib/wc2026";

interface GroupStageProps {
  standings: Record<string, GroupStanding[]>;
  onStandingsUpdate: (groupName: string, standings: GroupStanding[]) => void;
  onSimulateAll: () => void;
  simulatingAll: boolean;
  simulationProgress: number;
}

export default function GroupStage({
  standings,
  onStandingsUpdate,
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
          {completedGroups}/12 groups simulated
        </div>
        <button
          onClick={onSimulateAll}
          disabled={simulatingAll}
          className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {simulatingAll
            ? `Simulating... ${simulationProgress}/72`
            : allGroupsSimulated
              ? "Re-simulate All"
              : "Simulate All Groups"}
        </button>
      </div>

      {simulatingAll && (
        <div className="w-full bg-zinc-800 rounded-full h-2">
          <div
            className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(simulationProgress / 72) * 100}%` }}
          />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {GROUPS.map((group) => (
          <GroupCard
            key={group.name}
            group={group}
            standings={standings[group.name] || null}
            onStandingsUpdate={onStandingsUpdate}
          />
        ))}
      </div>
    </div>
  );
}
