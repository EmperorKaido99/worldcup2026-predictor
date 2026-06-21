"use client";

import { useState, useCallback, useEffect } from "react";
import GroupStage from "@/components/GroupStage";
import BracketView from "@/components/BracketView";
import {
  GROUPS,
  BRACKET_TEMPLATE,
  GroupStanding,
  BracketMatch,
  getGroupMatches,
  computeStandings,
  estimateGoals,
} from "@/lib/wc2026";
import { predictMatch, getWc2026LiveResults } from "@/lib/api";
import type { LiveMatchResult } from "@/components/GroupCard";

const STORAGE_KEY = "wc2026-tournament-state";

interface MatchResult {
  homeGoals: number;
  awayGoals: number;
  probs: { home_win: number; draw: number; away_win: number };
}

interface TournamentState {
  standings: Record<string, GroupStanding[]>;
  bracket: BracketMatch[];
  matchResults: Record<string, Record<string, MatchResult>>;
}

function loadState(): TournamentState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveState(state: TournamentState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // localStorage might be full
  }
}

export default function TournamentPage() {
  const [activeTab, setActiveTab] = useState<"groups" | "bracket">("groups");
  const [standings, setStandings] = useState<Record<string, GroupStanding[]>>({});
  const [bracket, setBracket] = useState<BracketMatch[]>(BRACKET_TEMPLATE);
  const [matchResults, setMatchResults] = useState<Record<string, Record<string, MatchResult>>>({});
  const [simulatingAll, setSimulatingAll] = useState(false);
  const [simulationProgress, setSimulationProgress] = useState(0);
  const [liveResults, setLiveResults] = useState<Record<string, Record<string, LiveMatchResult>>>({});

  // Load saved state on mount
  useEffect(() => {
    const saved = loadState();
    if (saved) {
      setStandings(saved.standings);
      setBracket(saved.bracket);
      if (saved.matchResults) setMatchResults(saved.matchResults);
    }
  }, []);

  // Fetch live WC2026 results on mount
  useEffect(() => {
    async function fetchLive() {
      try {
        const data = await getWc2026LiveResults();
        if (data.matches && data.matches.length > 0) {
          // Organize by group
          const byGroup: Record<string, Record<string, LiveMatchResult>> = {};
          for (const m of data.matches) {
            // Find which group this match belongs to
            for (const group of GROUPS) {
              const teamIds = group.teams.map((t) => t.id);
              if (teamIds.includes(m.home_id) && teamIds.includes(m.away_id)) {
                if (!byGroup[group.name]) byGroup[group.name] = {};
                const key = `${m.home_id}-${m.away_id}`;
                byGroup[group.name][key] = {
                  homeGoals: m.home_score,
                  awayGoals: m.away_score,
                };
                break;
              }
            }
          }
          setLiveResults(byGroup);

          // Auto-compute standings from live results
          const liveStandings: Record<string, GroupStanding[]> = {};
          for (const group of GROUPS) {
            const groupLive = byGroup[group.name];
            if (groupLive && Object.keys(groupLive).length > 0) {
              const goalResults: Record<string, { homeGoals: number; awayGoals: number }> = {};
              for (const [key, val] of Object.entries(groupLive)) {
                goalResults[key] = { homeGoals: val.homeGoals, awayGoals: val.awayGoals };
              }
              liveStandings[group.name] = computeStandings(group, goalResults);
            }
          }
          if (Object.keys(liveStandings).length > 0) {
            setStandings((prev) => ({ ...liveStandings, ...prev }));
          }
        }
      } catch {
        // Silently fail — live results are optional
      }
    }
    fetchLive();
  }, []);

  // Save state on change
  useEffect(() => {
    if (Object.keys(standings).length > 0 || bracket !== BRACKET_TEMPLATE) {
      saveState({ standings, bracket, matchResults });
    }
  }, [standings, bracket, matchResults]);

  const handleStandingsUpdate = useCallback(
    (groupName: string, groupStandings: GroupStanding[]) => {
      setStandings((prev) => ({ ...prev, [groupName]: groupStandings }));
    },
    []
  );

  const handleMatchResultsUpdate = useCallback(
    (groupName: string, results: Record<string, MatchResult>) => {
      setMatchResults((prev) => ({ ...prev, [groupName]: results }));
    },
    []
  );

  const handleSimulateAll = useCallback(async () => {
    setSimulatingAll(true);
    setSimulationProgress(0);

    const newStandings: Record<string, GroupStanding[]> = {};
    const newMatchResults: Record<string, Record<string, MatchResult>> = {};
    let progress = 0;

    // Count only simulatable matches for progress bar
    const totalSimulatable = GROUPS.reduce((acc, group) => {
      const groupLive = liveResults[group.name] || {};
      const matches = getGroupMatches(group);
      return acc + matches.filter((m) => !groupLive[`${m.home.id}-${m.away.id}`]).length;
    }, 0);

    for (const group of GROUPS) {
      const matches = getGroupMatches(group);
      const groupLive = liveResults[group.name] || {};
      const results: Record<string, { homeGoals: number; awayGoals: number }> = {};
      const groupResults: Record<string, MatchResult> = {};

      // Include live results in standings
      for (const [key, val] of Object.entries(groupLive)) {
        results[key] = { homeGoals: val.homeGoals, awayGoals: val.awayGoals };
      }

      // Only simulate matches that haven't been played
      const unplayedMatches = matches.filter(
        (m) => !groupLive[`${m.home.id}-${m.away.id}`]
      );

      if (unplayedMatches.length > 0) {
        const predictions = await Promise.all(
          unplayedMatches.map((m) =>
            predictMatch({ home: m.home.id, away: m.away.id, neutral: true })
          )
        );

        predictions.forEach((pred, i) => {
          const match = unplayedMatches[i];
          const goals = estimateGoals(pred.probabilities, pred.expected_goals);
          const key = `${match.home.id}-${match.away.id}`;
          results[key] = goals;
          groupResults[key] = { ...goals, probs: pred.probabilities };
          progress++;
          setSimulationProgress(progress);
        });
      }

      newStandings[group.name] = computeStandings(group, results);
      newMatchResults[group.name] = groupResults;
    }

    setStandings(newStandings);
    setMatchResults(newMatchResults);
    setSimulatingAll(false);
  }, [liveResults]);

  const handleBracketUpdate = useCallback((updated: BracketMatch[]) => {
    setBracket(updated);
  }, []);

  const handleReset = useCallback(() => {
    setStandings({});
    setBracket(BRACKET_TEMPLATE);
    setMatchResults({});
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const allGroupsSimulated = Object.keys(standings).length === 12;

  return (
    <div className="space-y-6">
      {/* Hero header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-950/50 via-zinc-900 to-zinc-900 border border-zinc-800 p-6">
        <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl" />
        <h1 className="text-3xl font-bold tracking-tight">
          World Cup 2026 <span className="text-emerald-400">Predictor</span>
        </h1>
        <p className="text-zinc-400 mt-1 text-sm">
          AI-powered match predictions &middot; Click any match to simulate
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setActiveTab("groups")}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
            activeTab === "groups"
              ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/20"
              : "bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700"
          }`}
        >
          Group Stage
        </button>
        <button
          onClick={() => setActiveTab("bracket")}
          disabled={!allGroupsSimulated}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
            activeTab === "bracket"
              ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/20"
              : "bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700"
          } disabled:opacity-30 disabled:cursor-not-allowed`}
        >
          Knockout Bracket
          {!allGroupsSimulated && (
            <span className="ml-1.5 text-[10px] opacity-70">(complete groups first)</span>
          )}
        </button>
        <div className="flex-1" />
        <button
          onClick={handleReset}
          className="px-3 py-2 rounded-xl text-xs text-zinc-500 hover:text-rose-400 hover:bg-zinc-800/50 transition-colors"
        >
          Reset All
        </button>
      </div>

      {/* Content */}
      {activeTab === "groups" && (
        <GroupStage
          standings={standings}
          matchResults={matchResults}
          liveResults={liveResults}
          onStandingsUpdate={handleStandingsUpdate}
          onMatchResultsUpdate={handleMatchResultsUpdate}
          onSimulateAll={handleSimulateAll}
          simulatingAll={simulatingAll}
          simulationProgress={simulationProgress}
        />
      )}

      {activeTab === "bracket" && allGroupsSimulated && (
        <BracketView
          bracket={bracket}
          groupStandings={standings}
          onBracketUpdate={handleBracketUpdate}
        />
      )}
    </div>
  );
}
