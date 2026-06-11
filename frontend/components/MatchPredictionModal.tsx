"use client";

import { useEffect, useState } from "react";
import TeamBadge from "./TeamBadge";
import ProbabilityBar from "./ProbabilityBar";
import { predictMatch, PredictMatchResponse } from "@/lib/api";

interface MatchPredictionModalProps {
  team1: string;
  team2: string;
  team1Name: string;
  team2Name: string;
  onPickWinner: (winnerId: string, probs: { home_win: number; draw: number; away_win: number }) => void;
  onClose: () => void;
}

export default function MatchPredictionModal({
  team1,
  team2,
  team1Name,
  team2Name,
  onPickWinner,
  onClose,
}: MatchPredictionModalProps) {
  const [prediction, setPrediction] = useState<PredictMatchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
  }, [team1, team2]);

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-zinc-900 border border-zinc-800 rounded-t-2xl md:rounded-2xl w-full max-w-md mx-auto p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg">Match Prediction</h3>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-white text-xl"
          >
            &times;
          </button>
        </div>

        <div className="flex items-center justify-around text-center">
          <div className="space-y-1">
            <TeamBadge teamId={team1} teamName={team1Name} size="lg" showName={false} />
            <div className="text-sm font-medium">{team1Name}</div>
          </div>
          <span className="text-zinc-600 font-bold text-sm">VS</span>
          <div className="space-y-1">
            <TeamBadge teamId={team2} teamName={team2Name} size="lg" showName={false} />
            <div className="text-sm font-medium">{team2Name}</div>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-4">
            <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <span className="ml-2 text-sm text-zinc-400">Predicting...</span>
          </div>
        )}

        {error && (
          <div className="text-rose-400 text-sm text-center py-2">{error}</div>
        )}

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
                <div className="text-zinc-500">{team1Name}</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-amber-400">
                  {Math.round(prediction.probabilities.draw * 100)}%
                </div>
                <div className="text-zinc-500">Draw</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-rose-400">
                  {Math.round(prediction.probabilities.away_win * 100)}%
                </div>
                <div className="text-zinc-500">{team2Name}</div>
              </div>
            </div>

            <div className="text-xs text-zinc-500 text-center">
              Pick the winner to advance:
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => onPickWinner(team1, prediction.probabilities)}
                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-emerald-600/20 border border-emerald-600/40 hover:bg-emerald-600/30 hover:border-emerald-500 transition-colors"
              >
                <TeamBadge teamId={team1} teamName={team1Name} size="sm" />
              </button>
              <button
                onClick={() => onPickWinner(team2, prediction.probabilities)}
                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-emerald-600/20 border border-emerald-600/40 hover:bg-emerald-600/30 hover:border-emerald-500 transition-colors"
              >
                <TeamBadge teamId={team2} teamName={team2Name} size="sm" />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
