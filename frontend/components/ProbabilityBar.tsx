"use client";

interface ProbabilityBarProps {
  homeWin: number;
  draw: number;
  awayWin: number;
}

export default function ProbabilityBar({
  homeWin,
  draw,
  awayWin,
}: ProbabilityBarProps) {
  const homePct = Math.round(homeWin * 100);
  const drawPct = Math.round(draw * 100);
  const awayPct = 100 - homePct - drawPct;

  return (
    <div className="w-full">
      <div className="flex w-full h-10 rounded-full overflow-hidden">
        {homePct > 0 && (
          <div
            className="bg-emerald-500 flex items-center justify-center text-xs font-bold text-white transition-all duration-500"
            style={{ width: `${homePct}%` }}
          >
            {homePct >= 10 && `${homePct}%`}
          </div>
        )}
        {drawPct > 0 && (
          <div
            className="bg-amber-500 flex items-center justify-center text-xs font-bold text-white transition-all duration-500"
            style={{ width: `${drawPct}%` }}
          >
            {drawPct >= 10 && `${drawPct}%`}
          </div>
        )}
        {awayPct > 0 && (
          <div
            className="bg-rose-500 flex items-center justify-center text-xs font-bold text-white transition-all duration-500"
            style={{ width: `${awayPct}%` }}
          >
            {awayPct >= 10 && `${awayPct}%`}
          </div>
        )}
      </div>
      <div className="flex justify-between mt-2 text-xs text-zinc-400">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
          Home Win
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
          Draw
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
          Away Win
        </span>
      </div>
    </div>
  );
}
