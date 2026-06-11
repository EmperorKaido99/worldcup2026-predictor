"use client";

import { useState, useEffect } from "react";
import {
  getXgStats,
  getXgShotMapUrl,
  getXgHeatmapUrl,
  getXgTeamsWithData,
  XgStats,
} from "@/lib/api";
import { GROUPS } from "@/lib/wc2026";
import { getFlag } from "@/lib/flags";

// Only WC2026 teams
const ALL_TEAMS = GROUPS.flatMap((g) =>
  g.teams.map((t) => ({ id: t.id, name: t.name }))
).sort((a, b) => a.name.localeCompare(b.name));

export default function XgDashboard() {
  const [selectedTeam, setSelectedTeam] = useState<string>("");
  const [stats, setStats] = useState<XgStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<"shotmap" | "heatmap">("shotmap");
  const [imgError, setImgError] = useState(false);
  const [teamsWithData, setTeamsWithData] = useState<Set<string>>(new Set());

  // Load which teams have data on mount
  useEffect(() => {
    getXgTeamsWithData()
      .then((teams) => setTeamsWithData(new Set(teams)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedTeam) {
      setStats(null);
      return;
    }

    setLoading(true);
    setError(null);
    setImgError(false);

    getXgStats(selectedTeam)
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load xG data");
        setLoading(false);
      });
  }, [selectedTeam]);

  const imgUrl =
    activeView === "shotmap"
      ? getXgShotMapUrl(selectedTeam)
      : getXgHeatmapUrl(selectedTeam);

  const teamsAvailable = ALL_TEAMS.filter((t) => teamsWithData.has(t.id));
  const teamsUnavailable = ALL_TEAMS.filter((t) => !teamsWithData.has(t.id));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-amber-950/40 via-zinc-900 to-zinc-900 border border-zinc-800 p-6">
        <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-3xl" />
        <h1 className="text-3xl font-bold tracking-tight">
          xG <span className="text-amber-400">Dashboard</span>
        </h1>
        <p className="text-zinc-400 mt-1 text-sm">
          Shot maps and expected goals from StatsBomb World Cup data
        </p>
      </div>

      {/* Team selector */}
      <div className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800">
        <label className="block text-sm font-medium text-zinc-400 mb-2">
          Select Team
          {teamsWithData.size > 0 && (
            <span className="text-zinc-600 ml-2">
              ({teamsAvailable.length} teams with data)
            </span>
          )}
        </label>
        <select
          value={selectedTeam}
          onChange={(e) => setSelectedTeam(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
        >
          <option value="">Choose a team...</option>
          {teamsAvailable.length > 0 && (
            <optgroup label="Teams with shot data">
              {teamsAvailable.map((team) => (
                <option key={team.id} value={team.id}>
                  {getFlag(team.id)} {team.name}
                </option>
              ))}
            </optgroup>
          )}
          {teamsUnavailable.length > 0 && teamsWithData.size > 0 && (
            <optgroup label="No shot data available">
              {teamsUnavailable.map((team) => (
                <option key={team.id} value={team.id}>
                  {getFlag(team.id)} {team.name}
                </option>
              ))}
            </optgroup>
          )}
          {teamsWithData.size === 0 &&
            ALL_TEAMS.map((team) => (
              <option key={team.id} value={team.id}>
                {getFlag(team.id)} {team.name}
              </option>
            ))}
        </select>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-3 text-zinc-400">Loading xG data...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-4 text-rose-400 text-sm">
          {error}
        </div>
      )}

      {/* Stats + Visuals */}
      {stats && !loading && (
        <>
          {stats.total_shots === 0 ? (
            <div className="bg-zinc-900 rounded-2xl p-8 border border-zinc-800 text-center">
              <div className="text-3xl mb-3">&#128269;</div>
              <h3 className="font-semibold mb-1">No Shot Data Available</h3>
              <p className="text-zinc-500 text-sm max-w-sm mx-auto">
                This team doesn&apos;t have shot-level data in the StatsBomb
                open dataset. Try selecting a team that played in the 2018 or
                2022 World Cup.
              </p>
            </div>
          ) : (
            <>
              {/* Summary stats strip */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="Total Shots" value={stats.total_shots} />
                <StatCard label="Goals" value={stats.goals} accent="emerald" />
                <StatCard
                  label="Total xG"
                  value={stats.total_xg.toFixed(1)}
                  accent="amber"
                />
                <StatCard
                  label="xG per Shot"
                  value={stats.xg_per_shot.toFixed(3)}
                />
              </div>

              {/* Conversion rate bar */}
              <div className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800">
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-zinc-400">Conversion Rate</span>
                  <span className="font-bold text-emerald-400">
                    {(stats.conversion_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                    style={{ width: `${stats.conversion_rate * 100}%` }}
                  />
                </div>
              </div>

              {/* Top scorers */}
              {stats.top_scorers.length > 0 && (
                <div className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800">
                  <h3 className="text-sm font-medium text-zinc-400 mb-3">
                    Top Scorers
                  </h3>
                  <div className="space-y-2">
                    {stats.top_scorers.map((scorer, i) => (
                      <div
                        key={scorer.player}
                        className="flex items-center justify-between text-sm"
                      >
                        <span className="text-zinc-300">
                          <span className="text-zinc-600 mr-2">{i + 1}.</span>
                          {scorer.player}
                        </span>
                        <span className="font-bold text-emerald-400">
                          {scorer.goals}{" "}
                          {scorer.goals === 1 ? "goal" : "goals"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* View toggle */}
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setActiveView("shotmap");
                    setImgError(false);
                  }}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                    activeView === "shotmap"
                      ? "bg-amber-600 text-white"
                      : "bg-zinc-800 text-zinc-400 hover:text-white"
                  }`}
                >
                  Shot Map
                </button>
                <button
                  onClick={() => {
                    setActiveView("heatmap");
                    setImgError(false);
                  }}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                    activeView === "heatmap"
                      ? "bg-amber-600 text-white"
                      : "bg-zinc-800 text-zinc-400 hover:text-white"
                  }`}
                >
                  Heatmap
                </button>
              </div>

              {/* Pitch visualization */}
              <div className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
                {imgError ? (
                  <div className="p-12 text-center text-zinc-500 text-sm">
                    Shot map not available. The backend may still be deploying.
                  </div>
                ) : (
                  <img
                    key={`${selectedTeam}-${activeView}`}
                    src={imgUrl}
                    alt={`${stats.team} ${activeView}`}
                    className="w-full"
                    onError={() => setImgError(true)}
                  />
                )}
              </div>
            </>
          )}
        </>
      )}

      {/* Empty state */}
      {!selectedTeam && !loading && (
        <div className="bg-zinc-900 rounded-2xl p-12 border border-zinc-800 text-center">
          <div className="text-4xl mb-4">&#x26BD;</div>
          <h2 className="text-lg font-semibold mb-2">Select a Team</h2>
          <p className="text-zinc-500 text-sm max-w-sm mx-auto">
            Choose a World Cup 2026 team above to view their shot map, heatmap,
            and xG statistics from recent tournament data.
          </p>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: "emerald" | "amber" | "rose";
}) {
  const colorClass =
    accent === "emerald"
      ? "text-emerald-400"
      : accent === "amber"
        ? "text-amber-400"
        : accent === "rose"
          ? "text-rose-400"
          : "text-white";

  return (
    <div className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800 text-center">
      <div className={`text-2xl font-bold ${colorClass}`}>{value}</div>
      <div className="text-xs text-zinc-500 mt-1">{label}</div>
    </div>
  );
}
