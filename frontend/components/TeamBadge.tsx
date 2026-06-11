"use client";

import { getFlag } from "@/lib/flags";

interface TeamBadgeProps {
  teamId: string;
  teamName?: string;
  size?: "sm" | "md" | "lg";
  showName?: boolean;
}

export default function TeamBadge({
  teamId,
  teamName,
  size = "md",
  showName = true,
}: TeamBadgeProps) {
  const flag = getFlag(teamId);
  const sizeClasses = {
    sm: "text-sm gap-1",
    md: "text-base gap-1.5",
    lg: "text-lg gap-2",
  };
  const flagSize = {
    sm: "text-base",
    md: "text-xl",
    lg: "text-2xl",
  };

  return (
    <span className={`inline-flex items-center ${sizeClasses[size]}`}>
      <span className={flagSize[size]}>{flag}</span>
      {showName && (
        <span className="truncate">
          {teamName || teamId}
        </span>
      )}
    </span>
  );
}
