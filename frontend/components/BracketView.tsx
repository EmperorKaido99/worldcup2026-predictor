"use client";

import { useState } from "react";
import BracketMatch from "./BracketMatch";
import MatchPredictionModal from "./MatchPredictionModal";
import TeamBadge from "./TeamBadge";
import {
  BracketMatch as BracketMatchType,
  GroupStanding,
  ROUND_NAMES,
  resolveSource,
  GROUPS,
} from "@/lib/wc2026";

interface BracketViewProps {
  bracket: BracketMatchType[];
  groupStandings: Record<string, GroupStanding[]>;
  onBracketUpdate: (bracket: BracketMatchType[]) => void;
}

const ROUND_ORDER = ["R32", "R16", "QF", "SF", "F"] as const;

function getTeamName(teamId: string): string {
  for (const group of GROUPS) {
    const team = group.teams.find((t) => t.id === teamId);
    if (team) return team.name;
  }
  return teamId;
}

export default function BracketView({
  bracket,
  groupStandings,
  onBracketUpdate,
}: BracketViewProps) {
  const [activeRound, setActiveRound] = useState<string>("R32");
  const [predictingMatch, setPredictingMatch] = useState<string | null>(null);

  // Resolve all bracket teams from sources
  const resolvedBracket = bracket.map((match) => ({
    ...match,
    team1: match.team1 || resolveSource(match.team1Source, groupStandings, bracket),
    team2: match.team2 || resolveSource(match.team2Source, groupStandings, bracket),
  }));

  function handlePickWinner(
    matchId: string,
    winnerId: string,
    probs: { home_win: number; draw: number; away_win: number }
  ) {
    const updated = bracket.map((m) =>
      m.id === matchId
        ? {
            ...m,
            winner: winnerId,
            probabilities: probs,
            team1: resolvedBracket.find((r) => r.id === matchId)?.team1,
            team2: resolvedBracket.find((r) => r.id === matchId)?.team2,
          }
        : m
    );
    onBracketUpdate(updated);
    setPredictingMatch(null);
  }

  const matchesByRound = (round: string) =>
    resolvedBracket.filter((m) => m.round === round);

  // Check if the champion is decided
  const finalMatch = resolvedBracket.find((m) => m.round === "F");
  const champion = finalMatch?.winner;

  // Count decided matches per round
  const roundProgress = ROUND_ORDER.map((r) => {
    const matches = matchesByRound(r);
    const decided = matches.filter((m) => m.winner).length;
    return { round: r, total: matches.length, decided };
  });

  const predictingMatchData = predictingMatch
    ? resolvedBracket.find((m) => m.id === predictingMatch)
    : null;

  return (
    <div className="space-y-4">
      {champion && (
        <div className="bg-gradient-to-r from-emerald-600/20 via-emerald-500/10 to-emerald-600/20 border border-emerald-600/40 rounded-2xl p-6 text-center space-y-3">
          <div className="text-sm text-emerald-400 font-medium uppercase tracking-wider">
            Predicted Champion
          </div>
          <div className="flex items-center justify-center">
            <TeamBadge
              teamId={champion}
              teamName={getTeamName(champion)}
              size="lg"
            />
          </div>
          <div className="text-3xl">🏆</div>
        </div>
      )}

      {/* Mobile: round tabs */}
      <div className="flex gap-1 overflow-x-auto pb-2 md:hidden">
        {ROUND_ORDER.map((r) => {
          const prog = roundProgress.find((p) => p.round === r)!;
          return (
            <button
              key={r}
              onClick={() => setActiveRound(r)}
              className={`flex-shrink-0 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                activeRound === r
                  ? "bg-emerald-600 text-white"
                  : "bg-zinc-800 text-zinc-400 hover:text-white"
              }`}
            >
              {ROUND_NAMES[r]}
              {prog.decided > 0 && (
                <span className="ml-1 text-emerald-300">
                  {prog.decided}/{prog.total}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Mobile: show active round only */}
      <div className="md:hidden space-y-2">
        <h3 className="font-bold text-sm text-zinc-400">
          {ROUND_NAMES[activeRound]}
        </h3>
        {matchesByRound(activeRound).map((match) => (
          <BracketMatch
            key={match.id}
            team1={match.team1}
            team2={match.team2}
            team1Name={match.team1 ? getTeamName(match.team1) : undefined}
            team2Name={match.team2 ? getTeamName(match.team2) : undefined}
            winner={match.winner}
            onClick={() => setPredictingMatch(match.id)}
          />
        ))}
      </div>

      {/* Desktop: full bracket */}
      <div className="hidden md:block overflow-x-auto">
        <div className="flex gap-6 min-w-[1000px] items-start py-4">
          {ROUND_ORDER.map((round) => {
            const matches = matchesByRound(round);
            const gapClass =
              round === "R32"
                ? "gap-2"
                : round === "R16"
                  ? "gap-6"
                  : round === "QF"
                    ? "gap-14"
                    : round === "SF"
                      ? "gap-28"
                      : "gap-0";
            return (
              <div key={round} className="flex-shrink-0" style={{ width: round === "R32" ? 180 : 170 }}>
                <div className="text-xs font-bold text-zinc-500 mb-3 text-center uppercase tracking-wider">
                  {ROUND_NAMES[round]}
                </div>
                <div className={`flex flex-col ${gapClass}`}>
                  {matches.map((match) => (
                    <BracketMatch
                      key={match.id}
                      team1={match.team1}
                      team2={match.team2}
                      team1Name={
                        match.team1 ? getTeamName(match.team1) : undefined
                      }
                      team2Name={
                        match.team2 ? getTeamName(match.team2) : undefined
                      }
                      winner={match.winner}
                      onClick={() => setPredictingMatch(match.id)}
                      compact={round === "R32"}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Prediction modal */}
      {predictingMatchData &&
        predictingMatchData.team1 &&
        predictingMatchData.team2 && (
          <MatchPredictionModal
            team1={predictingMatchData.team1}
            team2={predictingMatchData.team2}
            team1Name={getTeamName(predictingMatchData.team1)}
            team2Name={getTeamName(predictingMatchData.team2)}
            onPickWinner={(winnerId, probs) =>
              handlePickWinner(predictingMatchData.id, winnerId, probs)
            }
            onClose={() => setPredictingMatch(null)}
          />
        )}
    </div>
  );
}
