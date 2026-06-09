export default function PenaltyPredictor() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Penalty Shootout Predictor
        </h1>
        <p className="text-zinc-400 mt-1">
          Shot placement prediction with probability heatmaps
        </p>
      </div>

      <div className="bg-zinc-900 rounded-2xl p-8 border border-zinc-800 text-center">
        <div className="text-5xl mb-4">{"\u{1F945}"}</div>
        <span className="inline-block px-3 py-1 bg-amber-500/10 text-amber-400 text-xs font-medium rounded-full mb-4">
          Stretch Goal
        </span>
        <h2 className="text-xl font-semibold mb-2">Coming Soon</h2>
        <p className="text-zinc-400 text-sm max-w-md mx-auto">
          Predict penalty shot placement and keeper dive direction using
          historical shootout data. Select a shooter and keeper to see a 3x3
          goal-grid probability heatmap.
        </p>
        <p className="text-zinc-600 text-xs mt-4">
          Note: Penalty dive direction data is limited. This feature is
          lower-confidence by design.
        </p>
      </div>
    </div>
  );
}
