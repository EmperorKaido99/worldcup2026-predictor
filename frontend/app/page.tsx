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
import { predictMatch } from "@/lib/api";

const STORAGE_KEY = "wc2026-tournament-state";

interface TournamentState {
  standings: Record<string, GroupStanding[]>;
  bracket: BracketMatch[];
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
  const [simulatingAll, setSimulatingAll] = useState(false);
  const [simulationProgress, setSimulationProgress] = useState(0);

  // Load saved state on mount
  useEffect(() => {
    const saved = loadState();
    if (saved) {
      setStandings(saved.standings);
      setBracket(saved.bracket);
    }
  }, []);

  // Save state on change
  useEffect(() => {
    if (Object.keys(standings).length > 0 || bracket !== BRACKET_TEMPLATE) {
      saveState({ standings, bracket });
    }
  }, [standings, bracket]);

  const handleStandingsUpdate = useCallback(
    (groupName: string, groupStandings: GroupStanding[]) => {
      setStandings((prev) => ({ ...prev, [groupName]: groupStandings }));
    },
    []
  );

  const handleSimulateAll = useCallback(async () => {
    setSimulatingAll(true);
    setSimulationProgress(0);

    const newStandings: Record<string, GroupStanding[]> = {};
    let progress = 0;

    for (const group of GROUPS) {
      const matches = getGroupMatches(group);
      const results: Record<string, { homeGoals: number; awayGoals: number }> = {};

      // Run group matches in parallel (6 per group)
      const predictions = await Promise.all(
        matches.map((m) =>
          predictMatch({ home: m.home.id, away: m.away.id, neutral: true })
        )
      );

      predictions.forEach((pred, i) => {
        const match = matches[i];
        const goals = estimateGoals(pred.probabilities);
        results[`${match.home.id}-${match.away.id}`] = goals;
        progress++;
        setSimulationProgress(progress);
      });

      newStandings[group.name] = computeStandings(group, results);
    }

    setStandings(newStandings);
    setSimulatingAll(false);
  }, []);

  const handleBracketUpdate = useCallback((updated: BracketMatch[]) => {
    setBracket(updated);
  }, []);

  const handleReset = useCallback(() => {
    setStandings({});
    setBracket(BRACKET_TEMPLATE);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const allGroupsSimulated = Object.keys(standings).length === 12;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          World Cup 2026 Predictor
        </h1>
        <p className="text-zinc-400 mt-1">
          Simulate the tournament with AI-powered match predictions
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setActiveTab("groups")}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            activeTab === "groups"
              ? "bg-emerald-600 text-white"
              : "bg-zinc-800 text-zinc-400 hover:text-white"
          }`}
        >
          Group Stage
        </button>
        <button
          onClick={() => setActiveTab("bracket")}
          disabled={!allGroupsSimulated}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            activeTab === "bracket"
              ? "bg-emerald-600 text-white"
              : "bg-zinc-800 text-zinc-400 hover:text-white"
          } disabled:opacity-30 disabled:cursor-not-allowed`}
        >
          Knockout Bracket
          {!allGroupsSimulated && (
            <span className="ml-1 text-xs">(simulate groups first)</span>
          )}
        </button>
        <div className="flex-1" />
        <button
          onClick={handleReset}
          className="px-3 py-2 rounded-xl text-xs text-zinc-500 hover:text-rose-400 hover:bg-zinc-800 transition-colors"
        >
          Reset
        </button>
      </div>

      {/* Content */}
      {activeTab === "groups" && (
        <GroupStage
          standings={standings}
          onStandingsUpdate={handleStandingsUpdate}
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
