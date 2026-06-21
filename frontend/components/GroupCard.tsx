"use client";

import { useState } from "react";
import TeamBadge from "./TeamBadge";
import MatchPredictionModal from "./MatchPredictionModal";
import {
  Group,
  GroupStanding,
  getGroupMatches,
  computeStandings,
  estimateGoals,
} from "@/lib/wc2026";
import { predictMatch } from "@/lib/api";

interface MatchResult {
  homeGoals: number;
  awayGoals: number;
  probs: { home_win: number; draw: number; away_win: number };
}

export interface LiveMatchResult {
  homeGoals: number;
  awayGoals: number;
}

interface GroupCardProps {
  group: Group;
  standings: GroupStanding[] | null;
  matchResults: Record<string, MatchResult>;
  liveResults?: Record<string, LiveMatchResult>;
  onStandingsUpdate: (groupName: string, standings: GroupStanding[]) => void;
  onMatchResultsUpdate: (groupName: string, results: Record<string, MatchResult>) => void;
}

export default function GroupCard({
  group,
  standings,
  matchResults,
  liveResults = {},
  onStandingsUpdate,
  onMatchResultsUpdate,
}: GroupCardProps) {
  const [simulating, setSimulating] = useState(false);
  const [predictingMatch, setPredictingMatch] = useState<{
    home: { id: string; name: string };
    away: { id: string; name: string };
    key: string;
  } | null>(null);

  const matches = getGroupMatches(group);
  const liveCount = Object.keys(liveResults).length;
  const simulatableMatches = matches.filter(
    (m) => !liveResults[`${m.home.id}-${m.away.id}`]
  );

  function recomputeStandings(results: Record<string, MatchResult>) {
    const goalResults: Record<string, { homeGoals: number; awayGoals: number }> = {};
    // Include live results first
    for (const [key, val] of Object.entries(liveResults)) {
      goalResults[key] = { homeGoals: val.homeGoals, awayGoals: val.awayGoals };
    }
    // Then add simulated results
    for (const [key, val] of Object.entries(results)) {
      goalResults[key] = { homeGoals: val.homeGoals, awayGoals: val.awayGoals };
    }
    if (Object.keys(goalResults).length === matches.length) {
      const newStandings = computeStandings(group, goalResults);
      onStandingsUpdate(group.name, newStandings);
    }
  }

  function handleMatchPredicted(
    matchKey: string,
    probs: { home_win: number; draw: number; away_win: number },
    expectedGoals?: { home: number; away: number }
  ) {
    const goals = estimateGoals(probs, expectedGoals);
    const newResults = {
      ...matchResults,
      [matchKey]: { ...goals, probs },
    };
    onMatchResultsUpdate(group.name, newResults);
    recomputeStandings(newResults);
    setPredictingMatch(null);
  }

  async function simulateAll() {
    setSimulating(true);
    try {
      const newResults: Record<string, MatchResult> = {};
      // Only simulate matches that haven't been played yet
      for (const match of simulatableMatches) {
        const key = `${match.home.id}-${match.away.id}`;
        const pred = await predictMatch({
          home: match.home.id,
          away: match.away.id,
          neutral: true,
        });
        const goals = estimateGoals(pred.probabilities, pred.expected_goals);
        newResults[key] = { ...goals, probs: pred.probabilities };
      }
      onMatchResultsUpdate(group.name, newResults);

      // Combine live + simulated for standings
      const goalResults: Record<string, { homeGoals: number; awayGoals: number }> = {};
      for (const [key, val] of Object.entries(liveResults)) {
        goalResults[key] = { homeGoals: val.homeGoals, awayGoals: val.awayGoals };
      }
      for (const [key, val] of Object.entries(newResults)) {
        goalResults[key] = { homeGoals: val.homeGoals, awayGoals: val.awayGoals };
      }
      const newStandings = computeStandings(group, goalResults);
      onStandingsUpdate(group.name, newStandings);
    } catch {
      // silently fail
    } finally {
      setSimulating(false);
    }
  }

  const simulatedCount = Object.keys(matchResults).length;
  const allSimulated = simulatedCount >= simulatableMatches.length;
  const allDone = liveCount === matches.length; // All 6 matches played live

  return (
    <div className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-900/50">
        <h3 className="font-bold text-lg">
          Group <span className="text-emerald-400">{group.name}</span>
        </h3>
        <div className="flex items-center gap-2">
          {liveCount > 0 && (
            <span className="text-[10px] text-zinc-500">
              {liveCount} played{simulatableMatches.length > 0 && simulatedCount > 0 ? ` · ${simulatedCount}/${simulatableMatches.length} sim` : ""}
            </span>
          )}
          {!liveCount && simulatedCount > 0 && !allSimulated && (
            <span className="text-[10px] text-zinc-500">{simulatedCount}/6</span>
          )}
          {allDone ? (
            <span className="text-xs px-3 py-1.5 rounded-lg bg-zinc-800/50 border border-zinc-700/50 text-zinc-500">
              All Played
            </span>
          ) : (
            <button
              onClick={simulateAll}
              disabled={simulating}
              className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600/20 border border-emerald-600/40 hover:bg-emerald-600/30 text-emerald-400 hover:text-emerald-300 transition-all disabled:opacity-50"
            >
              {simulating ? (
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                  Simulating...
                </span>
              ) : allSimulated ? (
                "Re-simulate"
              ) : simulatableMatches.length < matches.length ? (
                `Simulate Remaining`
              ) : (
                "Simulate All"
              )}
            </button>
          )}
        </div>
      </div>

      {/* Standings table */}
      {standings && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-zinc-500 text-[10px] uppercase tracking-wider">
              <th className="text-left px-4 py-2">Team</th>
              <th className="w-7 text-center">P</th>
              <th className="w-7 text-center">W</th>
              <th className="w-7 text-center">D</th>
              <th className="w-7 text-center">L</th>
              <th className="w-8 text-center">GD</th>
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
                    : "border-l-2 border-l-transparent opacity-50";
              return (
                <tr key={s.teamId} className={`${rowColor} transition-colors`}>
                  <td className="px-4 py-1.5">
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
      )}

      {/* Match fixtures */}
      <div className="border-t border-zinc-800">
        <div className="px-4 py-2 text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
          Matches
        </div>
        <div className="px-3 pb-3 space-y-1.5">
          {matches.map((match) => {
            const key = `${match.home.id}-${match.away.id}`;
            const result = matchResults[key];
            const liveResult = liveResults[key];
            const isCompleted = !!liveResult;

            if (isCompleted) {
              // Completed match — greyed out, not clickable
              return (
                <div
                  key={key}
                  className="w-full rounded-lg px-3 py-2 text-sm bg-zinc-800/20 border border-zinc-800/40 opacity-60"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <TeamBadge teamId={match.home.id} teamName={match.home.name} size="sm" />
                    </div>
                    <div className="flex items-center gap-2 px-2 shrink-0">
                      <span className={`font-bold text-base tabular-nums ${
                        liveResult.homeGoals > liveResult.awayGoals ? "text-emerald-400" : "text-zinc-500"
                      }`}>
                        {liveResult.homeGoals}
                      </span>
                      <span className="text-zinc-700 text-xs">-</span>
                      <span className={`font-bold text-base tabular-nums ${
                        liveResult.awayGoals > liveResult.homeGoals ? "text-emerald-400" : "text-zinc-500"
                      }`}>
                        {liveResult.awayGoals}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 flex-1 min-w-0 justify-end">
                      <TeamBadge teamId={match.away.id} teamName={match.away.name} size="sm" />
                    </div>
                  </div>
                  <div className="text-[9px] text-zinc-600 text-center mt-1 uppercase tracking-wider">
                    Final
                  </div>
                </div>
              );
            }

            return (
              <button
                key={key}
                onClick={() =>
                  setPredictingMatch({
                    home: match.home,
                    away: match.away,
                    key,
                  })
                }
                className={`w-full rounded-lg px-3 py-2 text-sm transition-all ${
                  result
                    ? "bg-zinc-800/50 border border-zinc-700/50"
                    : "bg-zinc-800/30 border border-zinc-800 hover:border-emerald-600/50 hover:bg-zinc-800"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <TeamBadge teamId={match.home.id} teamName={match.home.name} size="sm" />
                  </div>
                  {result ? (
                    <div className="flex items-center gap-2 px-2 shrink-0">
                      <span className={`font-bold text-base tabular-nums ${
                        result.homeGoals > result.awayGoals ? "text-emerald-400" : "text-zinc-400"
                      }`}>
                        {result.homeGoals}
                      </span>
                      <span className="text-zinc-600 text-xs">-</span>
                      <span className={`font-bold text-base tabular-nums ${
                        result.awayGoals > result.homeGoals ? "text-emerald-400" : "text-zinc-400"
                      }`}>
                        {result.awayGoals}
                      </span>
                    </div>
                  ) : (
                    <span className="text-[10px] text-zinc-600 uppercase tracking-wider px-2 shrink-0">
                      vs
                    </span>
                  )}
                  <div className="flex items-center gap-2 flex-1 min-w-0 justify-end">
                    <TeamBadge teamId={match.away.id} teamName={match.away.name} size="sm" />
                  </div>
                </div>
                {result && (
                  <div className="flex mt-1.5 h-1 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-500 transition-all"
                      style={{ width: `${result.probs.home_win * 100}%` }}
                    />
                    <div
                      className="bg-amber-500 transition-all"
                      style={{ width: `${result.probs.draw * 100}%` }}
                    />
                    <div
                      className="bg-rose-500 transition-all"
                      style={{ width: `${result.probs.away_win * 100}%` }}
                    />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Prediction modal for individual match */}
      {predictingMatch && (
        <MatchPredictionModal
          team1={predictingMatch.home.id}
          team2={predictingMatch.away.id}
          team1Name={predictingMatch.home.name}
          team2Name={predictingMatch.away.name}
          onPickWinner={(_winnerId, probs, expectedGoals) =>
            handleMatchPredicted(predictingMatch.key, probs, expectedGoals)
          }
          onClose={() => setPredictingMatch(null)}
          isGroupMatch
        />
      )}
    </div>
  );
}
