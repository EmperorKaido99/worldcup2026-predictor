"use client";

import { useState, useEffect } from "react";
import { Team, PredictMatchResponse, getTeams, predictMatch } from "@/lib/api";
import { getFlag } from "@/lib/flags";
import TeamSelect from "@/components/TeamSelect";
import ProbabilityBar from "@/components/ProbabilityBar";
import LoadingSkeleton from "@/components/LoadingSkeleton";

const HOST_NATIONS = ["USA", "CAN", "MEX"];

export default function MatchPredictor() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [home, setHome] = useState("");
  const [away, setAway] = useState("");
  const [neutral, setNeutral] = useState(true);
  const [loading, setLoading] = useState(false);
  const [teamsLoading, setTeamsLoading] = useState(true);
  const [result, setResult] = useState<PredictMatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTeams()
      .then(setTeams)
      .catch((err) => setError(err.message))
      .finally(() => setTeamsLoading(false));
  }, []);

  // Auto-toggle neutral venue for host nations
  useEffect(() => {
    if (HOST_NATIONS.includes(home)) {
      setNeutral(false);
    } else {
      setNeutral(true);
    }
  }, [home]);

  const canPredict = home && away && home !== away && !loading;

  async function handlePredict() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await predictMatch({ home, away, neutral });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  }

  const homeName = teams.find((t) => t.id === home)?.name;
  const awayName = teams.find((t) => t.id === away)?.name;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Match Outcome Predictor
        </h1>
        <p className="text-zinc-400 mt-1">
          Predict 90-minute results for FIFA World Cup 2026
        </p>
      </div>

      {/* Team Selection Card */}
      <div className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800">
        {teamsLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-zinc-400">Loading teams...</span>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <TeamSelect
                teams={teams}
                value={home}
                onChange={setHome}
                label="Home Team"
                placeholder="Select home team..."
              />
              <TeamSelect
                teams={teams}
                value={away}
                onChange={setAway}
                label="Away Team"
                placeholder="Select away team..."
              />
            </div>

            {/* Neutral Venue Toggle */}
            <div className="flex items-center justify-between mt-4 px-1">
              <div>
                <span className="text-sm text-zinc-300">Neutral Venue</span>
                {!neutral && HOST_NATIONS.includes(home) && (
                  <span className="ml-2 text-xs text-amber-400">
                    (host nation home advantage)
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setNeutral(!neutral)}
                className={`relative w-11 h-6 rounded-full transition-colors ${
                  neutral ? "bg-emerald-500" : "bg-zinc-700"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                    neutral ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>

            {/* Predict Button */}
            <button
              onClick={handlePredict}
              disabled={!canPredict}
              className="w-full mt-5 py-3.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white font-semibold rounded-xl transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Predicting...
                </span>
              ) : (
                "Predict"
              )}
            </button>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-rose-950/50 border border-rose-800 rounded-2xl p-4 text-rose-300 text-sm">
          <p className="font-medium">Something went wrong</p>
          <p className="mt-1 text-rose-400">{error}</p>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && <LoadingSkeleton />}

      {/* Result Card */}
      {result && !loading && (
        <div className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800">
          {/* Teams header */}
          <div className="flex items-center justify-between mb-6">
            <div className="text-center">
              <div className="text-3xl mb-1">{getFlag(result.home)}</div>
              <div className="font-semibold text-sm">{homeName}</div>
            </div>
            <div className="text-zinc-600 text-sm font-medium">VS</div>
            <div className="text-center">
              <div className="text-3xl mb-1">{getFlag(result.away)}</div>
              <div className="font-semibold text-sm">{awayName}</div>
            </div>
          </div>

          {/* Probability Bar */}
          <ProbabilityBar
            homeWin={result.probabilities.home_win}
            draw={result.probabilities.draw}
            awayWin={result.probabilities.away_win}
          />

          {/* Large Numbers */}
          <div className="grid grid-cols-3 gap-4 mt-6 text-center">
            <div>
              <div className="text-4xl md:text-5xl font-bold text-emerald-400">
                {Math.round(result.probabilities.home_win * 100)}%
              </div>
              <div className="text-xs text-zinc-500 mt-1">Home Win</div>
            </div>
            <div>
              <div className="text-4xl md:text-5xl font-bold text-amber-400">
                {Math.round(result.probabilities.draw * 100)}%
              </div>
              <div className="text-xs text-zinc-500 mt-1">Draw</div>
            </div>
            <div>
              <div className="text-4xl md:text-5xl font-bold text-rose-400">
                {Math.round(result.probabilities.away_win * 100)}%
              </div>
              <div className="text-xs text-zinc-500 mt-1">Away Win</div>
            </div>
          </div>

          {/* Context */}
          <div className="mt-6 pt-5 border-t border-zinc-800">
            <h3 className="text-sm font-medium text-zinc-400 mb-3">
              Match Context
            </h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-zinc-800/50 rounded-lg p-3">
                <div className="text-zinc-500 text-xs">Elo Rating</div>
                <div className="font-mono font-semibold mt-0.5">
                  {result.context.elo_home}
                </div>
                <div className="text-zinc-500 text-xs mt-1">
                  {homeName}
                </div>
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3">
                <div className="text-zinc-500 text-xs">Elo Rating</div>
                <div className="font-mono font-semibold mt-0.5">
                  {result.context.elo_away}
                </div>
                <div className="text-zinc-500 text-xs mt-1">
                  {awayName}
                </div>
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3">
                <div className="text-zinc-500 text-xs">Recent Form</div>
                <div className="font-mono font-semibold mt-0.5 tracking-wider">
                  {result.context.form_home.split("").map((c, i) => (
                    <span
                      key={i}
                      className={
                        c === "W"
                          ? "text-emerald-400"
                          : c === "D"
                          ? "text-amber-400"
                          : "text-rose-400"
                      }
                    >
                      {c}
                    </span>
                  ))}
                </div>
                <div className="text-zinc-500 text-xs mt-1">
                  {homeName}
                </div>
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3">
                <div className="text-zinc-500 text-xs">Recent Form</div>
                <div className="font-mono font-semibold mt-0.5 tracking-wider">
                  {result.context.form_away.split("").map((c, i) => (
                    <span
                      key={i}
                      className={
                        c === "W"
                          ? "text-emerald-400"
                          : c === "D"
                          ? "text-amber-400"
                          : "text-rose-400"
                      }
                    >
                      {c}
                    </span>
                  ))}
                </div>
                <div className="text-zinc-500 text-xs mt-1">
                  {awayName}
                </div>
              </div>
            </div>
            <p className="text-xs text-zinc-600 mt-4">
              Predictions based on Elo ratings, recent form, and historical
              performance. Model: calibrated logistic regression on{" "}
              {result.neutral ? "neutral venue" : "home advantage"} setting.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
