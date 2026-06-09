export default function XgDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">xG Dashboard</h1>
        <p className="text-zinc-400 mt-1">
          Expected Goals model with shot maps and team dashboards
        </p>
      </div>

      <div className="bg-zinc-900 rounded-2xl p-8 border border-zinc-800 text-center">
        <div className="text-5xl mb-4">{"\u{1F4CA}"}</div>
        <span className="inline-block px-3 py-1 bg-amber-500/10 text-amber-400 text-xs font-medium rounded-full mb-4">
          Under Development
        </span>
        <h2 className="text-xl font-semibold mb-2">Coming Soon</h2>
        <p className="text-zinc-400 text-sm max-w-md mx-auto">
          Shot-level xG predictions using StatsBomb open data. Includes
          per-team shot maps, high-xG zone heatmaps, and position-filtered
          dashboards for forwards and midfielders.
        </p>
        <div className="mt-6 grid grid-cols-3 gap-4 max-w-sm mx-auto text-center">
          <div className="bg-zinc-800/50 rounded-lg p-3">
            <div className="text-lg font-bold text-zinc-300">Shots</div>
            <div className="text-xs text-zinc-500">Shot maps</div>
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-3">
            <div className="text-lg font-bold text-zinc-300">xG</div>
            <div className="text-xs text-zinc-500">Per shot</div>
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-3">
            <div className="text-lg font-bold text-zinc-300">Heatmaps</div>
            <div className="text-xs text-zinc-500">By position</div>
          </div>
        </div>
      </div>
    </div>
  );
}
