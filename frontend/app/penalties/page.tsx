"use client";

import { useState, useEffect } from "react";
import {
  getPenaltyStats,
  getTeamPenaltyStats,
  PenaltyStats,
  TeamPenaltyStats,
} from "@/lib/api";
import { GROUPS } from "@/lib/wc2026";
import { getFlag } from "@/lib/flags";

const ALL_TEAMS = GROUPS.flatMap((g) =>
  g.teams.map((t) => ({ id: t.id, name: t.name }))
).sort((a, b) => a.name.localeCompare(b.name));

// Zone labels for the 3x3 grid
const ZONE_LABELS = [
  "Bottom Left",
  "Bottom Center",
  "Bottom Right",
  "Mid Left",
  "Mid Center",
  "Mid Right",
  "Top Left",
  "Top Center",
  "Top Right",
];

export default function PenaltyPredictor() {
  const [overallStats, setOverallStats] = useState<PenaltyStats | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<string>("");
  const [teamStats, setTeamStats] = useState<TeamPenaltyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [teamLoading, setTeamLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPenaltyStats()
      .then((data) => {
        setOverallStats(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load penalty data");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedTeam) {
      setTeamStats(null);
      return;
    }
    setTeamLoading(true);
    getTeamPenaltyStats(selectedTeam)
      .then((data) => {
        setTeamStats(data);
        setTeamLoading(false);
      })
      .catch(() => setTeamLoading(false));
  }, [selectedTeam]);

  const activeStats = teamStats && teamStats.total > 0 ? teamStats : null;
  const activeZones = activeStats
    ? activeStats.zones
    : overallStats?.zone_stats || null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-rose-950/40 via-zinc-900 to-zinc-900 border border-zinc-800 p-6">
        <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/5 rounded-full blur-3xl" />
        <h1 className="text-3xl font-bold tracking-tight">
          Penalty <span className="text-rose-400">Predictor</span>
        </h1>
        <p className="text-zinc-400 mt-1 text-sm">
          Shot placement probabilities from World Cup penalty data
        </p>
      </div>

      {/* Team selector */}
      <div className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800">
        <label className="block text-sm font-medium text-zinc-400 mb-2">
          Filter by Team (optional)
        </label>
        <select
          value={selectedTeam}
          onChange={(e) => setSelectedTeam(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-transparent"
        >
          <option value="">All Teams (aggregate)</option>
          {ALL_TEAMS.map((team) => (
            <option key={team.id} value={team.id}>
              {getFlag(team.id)} {team.name}
            </option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-rose-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-3 text-zinc-400">Loading penalty data...</span>
        </div>
      )}

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-4 text-rose-400 text-sm">
          {error}
        </div>
      )}

      {activeZones && !loading && (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800 text-center">
              <div className="text-2xl font-bold text-white">
                {activeStats ? activeStats.total : overallStats?.total_penalties}
              </div>
              <div className="text-xs text-zinc-500 mt-1">Penalties</div>
            </div>
            <div className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800 text-center">
              <div className="text-2xl font-bold text-emerald-400">
                {activeStats ? activeStats.goals : overallStats?.total_goals}
              </div>
              <div className="text-xs text-zinc-500 mt-1">Scored</div>
            </div>
            <div className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800 text-center">
              <div className="text-2xl font-bold text-amber-400">
                {(
                  (activeStats
                    ? activeStats.conversion
                    : overallStats?.conversion_rate || 0) * 100
                ).toFixed(0)}
                %
              </div>
              <div className="text-xs text-zinc-500 mt-1">Conversion</div>
            </div>
          </div>

          {/* Goal Grid Heatmap */}
          <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
            <h3 className="text-sm font-medium text-zinc-400 mb-4 text-center">
              {activeStats
                ? `${activeStats.team} — Penalty Placement`
                : "All Penalties — Shot Placement Heatmap"}
            </h3>

            {/* Goal frame */}
            <div className="max-w-md mx-auto">
              {/* Goal posts top bar */}
              <div className="h-2 bg-white rounded-t-sm" />

              {/* 3x3 grid - rendered top to bottom (high, mid, low) */}
              <div className="border-l-4 border-r-4 border-white">
                {[2, 1, 0].map((row) => (
                  <div key={row} className="grid grid-cols-3 gap-1 p-1">
                    {[0, 1, 2].map((col) => {
                      const zone = row * 3 + col;
                      const stat = activeZones[String(zone)];
                      const prob = stat?.probability || 0;

                      // Color intensity based on probability
                      const intensity = Math.min(1, prob / 0.9);
                      const bg = prob > 0.7
                        ? `rgba(16, 185, 129, ${0.3 + intensity * 0.5})`  // emerald for high
                        : prob > 0.4
                          ? `rgba(245, 158, 11, ${0.3 + intensity * 0.4})`  // amber for mid
                          : `rgba(239, 68, 68, ${0.2 + intensity * 0.3})`;   // rose for low

                      return (
                        <div
                          key={zone}
                          className="aspect-[4/3] rounded-lg flex flex-col items-center justify-center transition-all hover:scale-105"
                          style={{ backgroundColor: bg }}
                        >
                          <div className="text-xl font-bold text-white">
                            {(prob * 100).toFixed(0)}%
                          </div>
                          <div className="text-[10px] text-zinc-300 mt-0.5">
                            {stat?.goals || 0}/{stat?.total || 0}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>

              {/* Ground line */}
              <div className="h-3 bg-emerald-900/50 rounded-b-lg border-t-2 border-white/50" />
            </div>

            {/* Labels */}
            <div className="flex justify-between max-w-md mx-auto mt-3 text-[10px] text-zinc-500 uppercase tracking-wider px-2">
              <span>Left</span>
              <span>Center</span>
              <span>Right</span>
            </div>

            {/* Legend */}
            <div className="flex justify-center gap-4 mt-4 text-xs text-zinc-500">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-emerald-500/50" />
                High scoring
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-amber-500/40" />
                Medium
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-rose-500/30" />
                Low scoring
              </span>
            </div>
          </div>

          {/* Insights */}
          {activeZones && (
            <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-4">
              <h3 className="text-sm font-medium text-zinc-400 mb-3">
                Key Insights
              </h3>
              <div className="space-y-2 text-sm text-zinc-300">
                {(() => {
                  const zones = Object.entries(activeZones)
                    .map(([z, s]) => ({ zone: parseInt(z), ...s }))
                    .filter((z) => z.total > 0)
                    .sort((a, b) => b.probability - a.probability);

                  if (zones.length === 0) return <p className="text-zinc-500">No data available</p>;

                  const best = zones[0];
                  const worst = zones[zones.length - 1];
                  const mostAttempted = [...zones].sort((a, b) => b.total - a.total)[0];

                  return (
                    <>
                      <div className="flex items-start gap-2">
                        <span className="text-emerald-400 mt-0.5">&#9650;</span>
                        <span>
                          Best zone: <strong>{ZONE_LABELS[best.zone]}</strong> —{" "}
                          {(best.probability * 100).toFixed(0)}% conversion ({best.goals}/{best.total})
                        </span>
                      </div>
                      <div className="flex items-start gap-2">
                        <span className="text-rose-400 mt-0.5">&#9660;</span>
                        <span>
                          Worst zone: <strong>{ZONE_LABELS[worst.zone]}</strong> —{" "}
                          {(worst.probability * 100).toFixed(0)}% conversion ({worst.goals}/{worst.total})
                        </span>
                      </div>
                      <div className="flex items-start gap-2">
                        <span className="text-amber-400 mt-0.5">&#9679;</span>
                        <span>
                          Most targeted: <strong>{ZONE_LABELS[mostAttempted.zone]}</strong> —{" "}
                          {mostAttempted.total} attempts
                        </span>
                      </div>
                    </>
                  );
                })()}
              </div>
            </div>
          )}

          {teamLoading && (
            <div className="flex items-center justify-center py-4">
              <div className="w-4 h-4 border-2 border-rose-500 border-t-transparent rounded-full animate-spin" />
              <span className="ml-2 text-sm text-zinc-400">Loading team data...</span>
            </div>
          )}

          {selectedTeam && teamStats && teamStats.total === 0 && !teamLoading && (
            <div className="bg-zinc-800/50 rounded-xl p-4 text-center text-sm text-zinc-500">
              No penalty data available for this team. Showing aggregate stats.
            </div>
          )}
        </>
      )}
    </div>
  );
}
