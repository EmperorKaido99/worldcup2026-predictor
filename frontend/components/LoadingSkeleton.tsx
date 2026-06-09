"use client";

export default function LoadingSkeleton() {
  return (
    <div className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800 animate-pulse">
      <div className="flex justify-between items-center mb-6">
        <div className="h-6 w-24 bg-zinc-800 rounded" />
        <div className="h-4 w-8 bg-zinc-800 rounded" />
        <div className="h-6 w-24 bg-zinc-800 rounded" />
      </div>
      <div className="h-10 w-full bg-zinc-800 rounded-full mb-4" />
      <div className="flex justify-between mb-6">
        <div className="h-12 w-20 bg-zinc-800 rounded" />
        <div className="h-12 w-20 bg-zinc-800 rounded" />
        <div className="h-12 w-20 bg-zinc-800 rounded" />
      </div>
      <div className="h-px bg-zinc-800 mb-4" />
      <div className="space-y-2">
        <div className="h-4 w-3/4 bg-zinc-800 rounded" />
        <div className="h-4 w-1/2 bg-zinc-800 rounded" />
      </div>
    </div>
  );
}
