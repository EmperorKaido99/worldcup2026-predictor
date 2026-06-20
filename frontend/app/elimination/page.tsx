"use client";

import { useState, useEffect } from "react";
import TeamBadge from "@/components/TeamBadge";
import { getEliminationRisk, type TeamRisk } from "@/lib/api";

const RISK_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string }
> = {
  qualified: {
    label: "Qualified",
    color: "text-emerald-300",
    bg: "bg-emerald-950/40",
    border: "border-emerald-700/50",
  },
  eliminated: {
    label: "Eliminated",
    color: "text-red-400",
    bg: "bg-red-950/30",
    border: "border-red-800/50",
  },
  critical: {
    label: "Critical",
    color: "text-red-400",
    bg: "bg-red-950/20",
    border: "border-red-800/30",
  },
  high: {
    label: "High Risk",
    color: "text-orange-400",
    bg: "bg-orange-950/20",
    border: "border-orange-800/30",
  },
  at_risk: {
    label: "At Risk",
    color: "text-amber-400",
    bg: "bg-amber-950/20",
    border: "border-amber-800/30",
  },
  contention: {
    label: "In Contention",
    color: "text-amber-300",
    bg: "bg-amber-950/10",
    border: "border-amber-800/20",
  },
  likely_safe: {
    label: "Likely Safe",
    color: "text-emerald-400",
    bg: "bg-emerald-950/20",
    border: "border-emerald-800/30",
  },
  safe: {
    label: "Safe",
    color: "text-emerald-400",
    bg: "bg-emerald-950/30",
    border: "border-emerald-800/50",
  },
  not_started: {
    label: "Not Started",
    color: "text-zinc-500",
    bg: "bg-zinc-900/30",
    border: "border-zinc-800/30",
  },
};

function RiskBadge({ risk }: { risk: string }) {
  const config = RISK_CONFIG[risk] || RISK_CONFIG.not_started;
  return (
    <span
      className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full ${config.color} ${config.bg} ${config.border} border`}
    >
      {config.label}
    </span>
  );
}

function RiskBar({ pct }: { pct: number }) {
  const color =
    pct >= 80
      ? "bg-red-500"
      : pct >= 60
        ? "bg-orange-500"
        : pct >= 40
          ? "bg-amber-500"
          : pct >= 20
            ? "bg-emerald-500"
            : "bg-emerald-400";
  return (
    <div className="w-20 bg-zinc-800 rounded-full h-1.5 overflow-hidden">
      <div
        className={`${color} h-1.5 rounded-full transition-all duration-500`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function EliminationPage() {
  const [data, setData] = useState<{
    groups: Record<string, TeamRisk[]>;
    matches_played: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"risk" | "groups">("risk");

  useEffect(() => {
    async function load() {
      try {
        const result = await getEliminationRisk();
        setData(result);
      } catch (e: unknown) {
        setError(
          e instanceof Error
            ? e.message
            : "Failed to load elimination data. The API may be starting up."
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl bg-zinc-900 border border-zinc-800 p-8 text-center">
          <div className="w-8 h-8 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-zinc-400 text-sm">
            Loading elimination tracker...
          </p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl bg-zinc-900 border border-zinc-800 p-8 text-center">
          <p className="text-rose-400 text-sm">{error || "No data available"}</p>
          <p className="text-zinc-500 text-xs mt-2">
            Make sure the backend API is running and has WC2026 data.
          </p>
        </div>
      </div>
    );
  }

  // Flatten all teams and sort by elimination risk (highest first)
  const allTeams: (TeamRisk & { group: string })[] = [];
  for (const [groupName, teams] of Object.entries(data.groups)) {
    for (const team of teams) {
      allTeams.push({ ...team, group: groupName });
    }
  }
  const teamsAtRisk = allTeams
    .filter((t) => t.risk !== "not_started")
    .sort((a, b) => b.risk_pct - a.risk_pct);

  const eliminatedCount = allTeams.filter(
    (t) => t.risk === "eliminated"
  ).length;
  const criticalCount = allTeams.filter(
    (t) => t.risk === "critical" || t.risk === "high"
  ).length;
  const safeCount = allTeams.filter(
    (t) => t.risk === "safe" || t.risk === "likely_safe"
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-red-950/30 via-zinc-900 to-zinc-900 border border-zinc-800 p-6">
        <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/5 rounded-full blur-3xl" />
        <h1 className="text-3xl font-bold tracking-tight">
          Elimination <span className="text-red-400">Tracker</span>
        </h1>
        <p className="text-zinc-400 mt-1 text-sm">
          Live group standings &middot; Teams at risk of elimination
        </p>
        <div className="flex gap-4 mt-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-white">
              {data.matches_played}
            </div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">
              Matches Played
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">
              {eliminatedCount}
            </div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">
              Eliminated
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-400">
              {criticalCount}
            </div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">
              At Risk
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-emerald-400">
              {safeCount}
            </div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">
              Safe
            </div>
          </div>
        </div>
      </div>

      {/* View toggle */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setView("risk")}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
            view === "risk"
              ? "bg-red-600 text-white shadow-lg shadow-red-600/20"
              : "bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700"
          }`}
        >
          By Risk Level
        </button>
        <button
          onClick={() => setView("groups")}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
            view === "groups"
              ? "bg-red-600 text-white shadow-lg shadow-red-600/20"
              : "bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700"
          }`}
        >
          By Group
        </button>
      </div>

      {/* Risk view — all teams sorted by elimination risk */}
      {view === "risk" && (
        <div className="space-y-2">
          {teamsAtRisk.length === 0 ? (
            <div className="rounded-2xl bg-zinc-900 border border-zinc-800 p-8 text-center">
              <p className="text-zinc-400 text-sm">
                No matches played yet. Check back once the tournament starts.
              </p>
            </div>
          ) : (
            teamsAtRisk.map((team) => {
              const config =
                RISK_CONFIG[team.risk] || RISK_CONFIG.not_started;
              return (
                <div
                  key={team.team_id}
                  className={`rounded-xl ${config.bg} border ${config.border} px-4 py-3 flex items-center gap-4`}
                >
                  <div className="w-8 text-center text-zinc-500 text-xs font-mono">
                    {team.group}
                  </div>
                  <div className="flex-1 min-w-0">
                    <TeamBadge
                      teamId={team.team_id}
                      teamName={team.team}
                      size="md"
                    />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-zinc-400 tabular-nums">
                    <span>
                      {team.played}P {team.won}W {team.drawn}D {team.lost}L
                    </span>
                    <span className="font-bold text-white">
                      {team.points}pts
                    </span>
                    <span className={team.gd > 0 ? "text-emerald-400" : team.gd < 0 ? "text-red-400" : ""}>
                      {team.gd > 0 ? `+${team.gd}` : team.gd}
                    </span>
                  </div>
                  <RiskBar pct={team.risk_pct} />
                  <RiskBadge risk={team.risk} />
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Group view — standings per group */}
      {view === "groups" && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Object.entries(data.groups)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([groupName, teams]) => (
              <div
                key={groupName}
                className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden"
              >
                <div className="px-4 py-3 border-b border-zinc-800 bg-zinc-900/50">
                  <h3 className="font-bold text-lg">
                    Group{" "}
                    <span className="text-emerald-400">{groupName}</span>
                  </h3>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-zinc-500 text-[10px] uppercase tracking-wider">
                      <th className="text-left px-4 py-2">Team</th>
                      <th className="w-7 text-center">P</th>
                      <th className="w-7 text-center">W</th>
                      <th className="w-7 text-center">D</th>
                      <th className="w-7 text-center">L</th>
                      <th className="w-8 text-center">GD</th>
                      <th className="w-10 text-center font-bold text-zinc-400">
                        Pts
                      </th>
                      <th className="w-24 text-center pr-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teams.map((team) => {
                      const config =
                        RISK_CONFIG[team.risk] || RISK_CONFIG.not_started;
                      const rowColor =
                        team.risk === "safe" || team.risk === "likely_safe" || team.risk === "qualified"
                          ? "bg-emerald-950/20 border-l-2 border-l-emerald-500"
                          : team.risk === "eliminated" || team.risk === "critical"
                            ? "bg-red-950/10 border-l-2 border-l-red-500"
                            : team.risk === "high" || team.risk === "at_risk"
                              ? "bg-orange-950/10 border-l-2 border-l-orange-500"
                              : team.risk === "contention"
                                ? "bg-amber-950/10 border-l-2 border-l-amber-500"
                                : "border-l-2 border-l-transparent";
                      return (
                        <tr
                          key={team.team_id}
                          className={`${rowColor} transition-colors`}
                        >
                          <td className="px-4 py-1.5">
                            <TeamBadge
                              teamId={team.team_id}
                              teamName={team.team}
                              size="sm"
                            />
                          </td>
                          <td className="text-center text-zinc-400">
                            {team.played}
                          </td>
                          <td className="text-center text-zinc-400">
                            {team.won}
                          </td>
                          <td className="text-center text-zinc-400">
                            {team.drawn}
                          </td>
                          <td className="text-center text-zinc-400">
                            {team.lost}
                          </td>
                          <td className="text-center text-zinc-400">
                            {team.gd > 0 ? `+${team.gd}` : team.gd}
                          </td>
                          <td className="text-center font-bold">
                            {team.points}
                          </td>
                          <td className="text-center pr-3">
                            <span
                              className={`text-[9px] uppercase tracking-wider font-bold ${config.color}`}
                            >
                              {config.label}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
