"use client";

import { useEffect, useState } from "react";
import TeamBadge from "./TeamBadge";
import ProbabilityBar from "./ProbabilityBar";
import { predictMatch, getXgStats, PredictMatchResponse, XgStats } from "@/lib/api";

interface MatchPredictionModalProps {
  team1: string;
  team2: string;
  team1Name: string;
  team2Name: string;
  onPickWinner: (winnerId: string, probs: { home_win: number; draw: number; away_win: number }, expectedGoals?: { home: number; away: number }) => void;
  onClose: () => void;
  isGroupMatch?: boolean;
}

export default function MatchPredictionModal({
  team1,
  team2,
  team1Name,
  team2Name,
  onPickWinner,
  onClose,
  isGroupMatch = false,
}: MatchPredictionModalProps) {
  const [prediction, setPrediction] = useState<PredictMatchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [xg1, setXg1] = useState<XgStats | null>(null);
  const [xg2, setXg2] = useState<XgStats | null>(null);

  useEffect(() => {
    async function predict() {
      try {
        const result = await predictMatch({
          home: team1,
          away: team2,
          neutral: true,
        });
        setPrediction(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Prediction failed");
      } finally {
        setLoading(false);
      }
    }
    predict();

    // Load xG stats in parallel (non-blocking)
    getXgStats(team1).then(setXg1).catch(() => {});
    getXgStats(team2).then(setXg2).catch(() => {});
  }, [team1, team2]);

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center animate-in fade-in duration-200">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-zinc-900 border border-zinc-800 rounded-t-2xl md:rounded-2xl w-full max-w-lg mx-auto p-6 space-y-5 animate-in slide-in-from-bottom-4 duration-300">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg">Match Prediction</h3>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-white w-8 h-8 rounded-lg hover:bg-zinc-800 flex items-center justify-center transition-colors text-xl"
          >
            &times;
          </button>
        </div>

        {/* Teams */}
        <div className="flex items-center justify-around text-center">
          <div className="space-y-1 flex-1">
            <TeamBadge teamId={team1} teamName={team1Name} size="lg" showName={false} />
            <div className="text-sm font-medium">{team1Name}</div>
            {xg1 && xg1.total_shots > 0 && (
              <div className="text-[10px] text-zinc-500 space-x-2">
                <span>{xg1.total_xg} xG</span>
                <span>&middot;</span>
                <span>{(xg1.conversion_rate * 100).toFixed(0)}% conv.</span>
              </div>
            )}
          </div>
          <div className="px-4">
            <span className="text-zinc-600 font-bold text-sm bg-zinc-800 rounded-lg px-3 py-1.5">VS</span>
          </div>
          <div className="space-y-1 flex-1">
            <TeamBadge teamId={team2} teamName={team2Name} size="lg" showName={false} />
            <div className="text-sm font-medium">{team2Name}</div>
            {xg2 && xg2.total_shots > 0 && (
              <div className="text-[10px] text-zinc-500 space-x-2">
                <span>{xg2.total_xg} xG</span>
                <span>&middot;</span>
                <span>{(xg2.conversion_rate * 100).toFixed(0)}% conv.</span>
              </div>
            )}
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-6">
            <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-sm text-zinc-400">Analyzing match...</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="text-rose-400 text-sm text-center py-2 bg-rose-500/10 rounded-xl px-4">
            {error}
          </div>
        )}

        {/* Prediction results */}
        {prediction && (
          <>
            <ProbabilityBar
              homeWin={prediction.probabilities.home_win}
              draw={prediction.probabilities.draw}
              awayWin={prediction.probabilities.away_win}
            />

            <div className="grid grid-cols-3 text-center text-sm">
              <div>
                <div className="text-2xl font-bold text-emerald-400">
                  {Math.round(prediction.probabilities.home_win * 100)}%
                </div>
                <div className="text-zinc-500 text-xs">{team1Name}</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-amber-400">
                  {Math.round(prediction.probabilities.draw * 100)}%
                </div>
                <div className="text-zinc-500 text-xs">Draw</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-rose-400">
                  {Math.round(prediction.probabilities.away_win * 100)}%
                </div>
                <div className="text-zinc-500 text-xs">{team2Name}</div>
              </div>
            </div>

            {/* Context: Elo + form */}
            {prediction.context && (
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-zinc-800/50 rounded-xl p-3 space-y-1.5">
                  <div className="text-zinc-500 font-medium">{team1Name}</div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Elo</span>
                    <span className="font-bold text-zinc-300">{prediction.context.elo_home}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Form</span>
                    <span className="font-mono tracking-wider">
                      {prediction.context.form_home.split("").map((c, i) => (
                        <span
                          key={i}
                          className={
                            c === "W" ? "text-emerald-400" : c === "D" ? "text-amber-400" : "text-rose-400"
                          }
                        >
                          {c}
                        </span>
                      ))}
                    </span>
                  </div>
                </div>
                <div className="bg-zinc-800/50 rounded-xl p-3 space-y-1.5">
                  <div className="text-zinc-500 font-medium">{team2Name}</div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Elo</span>
                    <span className="font-bold text-zinc-300">{prediction.context.elo_away}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Form</span>
                    <span className="font-mono tracking-wider">
                      {prediction.context.form_away.split("").map((c, i) => (
                        <span
                          key={i}
                          className={
                            c === "W" ? "text-emerald-400" : c === "D" ? "text-amber-400" : "text-rose-400"
                          }
                        >
                          {c}
                        </span>
                      ))}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Action buttons */}
            {isGroupMatch ? (
              <button
                onClick={() => onPickWinner(team1, prediction.probabilities, prediction.expected_goals)}
                className="w-full px-4 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors text-sm"
              >
                Accept Result
              </button>
            ) : (
              <>
                <div className="text-xs text-zinc-500 text-center">
                  Pick the winner to advance:
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => onPickWinner(team1, prediction.probabilities, prediction.expected_goals)}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-emerald-600/20 border border-emerald-600/40 hover:bg-emerald-600/30 hover:border-emerald-500 transition-colors"
                  >
                    <TeamBadge teamId={team1} teamName={team1Name} size="sm" />
                  </button>
                  <button
                    onClick={() => onPickWinner(team2, prediction.probabilities, prediction.expected_goals)}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-emerald-600/20 border border-emerald-600/40 hover:bg-emerald-600/30 hover:border-emerald-500 transition-colors"
                  >
                    <TeamBadge teamId={team2} teamName={team2Name} size="sm" />
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
