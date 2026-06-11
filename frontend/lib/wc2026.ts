// FIFA World Cup 2026 — Groups, bracket template, and types

export interface GroupTeam {
  id: string;
  name: string;
}

export interface Group {
  name: string;
  teams: GroupTeam[];
}

export interface GroupStanding {
  teamId: string;
  teamName: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
}

export interface BracketMatch {
  id: string;
  round: "R32" | "R16" | "QF" | "SF" | "F";
  team1Source: string;
  team2Source: string;
  team1?: string;
  team2?: string;
  winner?: string;
  probabilities?: { home_win: number; draw: number; away_win: number };
}

// Official FIFA World Cup 2026 Groups
export const GROUPS: Group[] = [
  {
    name: "A",
    teams: [
      { id: "MEX", name: "Mexico" },
      { id: "RSA", name: "South Africa" },
      { id: "KOR", name: "South Korea" },
      { id: "CZE", name: "Czechia" },
    ],
  },
  {
    name: "B",
    teams: [
      { id: "CAN", name: "Canada" },
      { id: "BIH", name: "Bosnia & Herzegovina" },
      { id: "QAT", name: "Qatar" },
      { id: "SUI", name: "Switzerland" },
    ],
  },
  {
    name: "C",
    teams: [
      { id: "BRA", name: "Brazil" },
      { id: "MAR", name: "Morocco" },
      { id: "HAI", name: "Haiti" },
      { id: "SCO", name: "Scotland" },
    ],
  },
  {
    name: "D",
    teams: [
      { id: "USA", name: "United States" },
      { id: "PAR", name: "Paraguay" },
      { id: "AUS", name: "Australia" },
      { id: "TUR", name: "Turkey" },
    ],
  },
  {
    name: "E",
    teams: [
      { id: "GER", name: "Germany" },
      { id: "CUW", name: "Curaçao" },
      { id: "CIV", name: "Ivory Coast" },
      { id: "ECU", name: "Ecuador" },
    ],
  },
  {
    name: "F",
    teams: [
      { id: "NED", name: "Netherlands" },
      { id: "JPN", name: "Japan" },
      { id: "SWE", name: "Sweden" },
      { id: "TUN", name: "Tunisia" },
    ],
  },
  {
    name: "G",
    teams: [
      { id: "BEL", name: "Belgium" },
      { id: "EGY", name: "Egypt" },
      { id: "IRN", name: "Iran" },
      { id: "NZL", name: "New Zealand" },
    ],
  },
  {
    name: "H",
    teams: [
      { id: "ESP", name: "Spain" },
      { id: "CPV", name: "Cape Verde" },
      { id: "KSA", name: "Saudi Arabia" },
      { id: "URU", name: "Uruguay" },
    ],
  },
  {
    name: "I",
    teams: [
      { id: "FRA", name: "France" },
      { id: "SEN", name: "Senegal" },
      { id: "IRQ", name: "Iraq" },
      { id: "NOR", name: "Norway" },
    ],
  },
  {
    name: "J",
    teams: [
      { id: "ARG", name: "Argentina" },
      { id: "ALG", name: "Algeria" },
      { id: "AUT", name: "Austria" },
      { id: "JOR", name: "Jordan" },
    ],
  },
  {
    name: "K",
    teams: [
      { id: "POR", name: "Portugal" },
      { id: "COD", name: "DR Congo" },
      { id: "UZB", name: "Uzbekistan" },
      { id: "COL", name: "Colombia" },
    ],
  },
  {
    name: "L",
    teams: [
      { id: "ENG", name: "England" },
      { id: "CRO", name: "Croatia" },
      { id: "GHA", name: "Ghana" },
      { id: "PAN", name: "Panama" },
    ],
  },
];

// All WC2026 team IDs (for filtering)
export const WC2026_TEAM_IDS = new Set(
  GROUPS.flatMap((g) => g.teams.map((t) => t.id))
);

// Get group matches (all 6 pairings for a group of 4)
export function getGroupMatches(
  group: Group
): { home: GroupTeam; away: GroupTeam }[] {
  const matches: { home: GroupTeam; away: GroupTeam }[] = [];
  for (let i = 0; i < group.teams.length; i++) {
    for (let j = i + 1; j < group.teams.length; j++) {
      matches.push({ home: group.teams[i], away: group.teams[j] });
    }
  }
  return matches;
}

// Compute standings from match results
export function computeStandings(
  group: Group,
  results: Record<string, { homeGoals: number; awayGoals: number }>
): GroupStanding[] {
  const standings: Record<string, GroupStanding> = {};
  for (const t of group.teams) {
    standings[t.id] = {
      teamId: t.id,
      teamName: t.name,
      played: 0,
      won: 0,
      drawn: 0,
      lost: 0,
      gf: 0,
      ga: 0,
      gd: 0,
      points: 0,
    };
  }

  for (const [key, result] of Object.entries(results)) {
    const [homeId, awayId] = key.split("-");
    if (!standings[homeId] || !standings[awayId]) continue;

    const h = standings[homeId];
    const a = standings[awayId];

    h.played++;
    a.played++;
    h.gf += result.homeGoals;
    h.ga += result.awayGoals;
    a.gf += result.awayGoals;
    a.ga += result.homeGoals;

    if (result.homeGoals > result.awayGoals) {
      h.won++;
      h.points += 3;
      a.lost++;
    } else if (result.homeGoals === result.awayGoals) {
      h.drawn++;
      h.points += 1;
      a.drawn++;
      a.points += 1;
    } else {
      a.won++;
      a.points += 3;
      h.lost++;
    }
  }

  // Update GD
  for (const s of Object.values(standings)) {
    s.gd = s.gf - s.ga;
  }

  // Sort: points desc, then GD desc, then GF desc
  return Object.values(standings).sort(
    (a, b) => b.points - a.points || b.gd - a.gd || b.gf - a.gf
  );
}

// Bracket template — R32 through Final
// Sources reference group positions: "1A" = winner of Group A, "2A" = runner-up, "3rd" = best 3rd place
export const BRACKET_TEMPLATE: BracketMatch[] = [
  // Round of 32 (16 matches) — group winners vs 3rd place, runners-up vs runners-up
  { id: "r32-1", round: "R32", team1Source: "1A", team2Source: "3C" },
  { id: "r32-2", round: "R32", team1Source: "1B", team2Source: "3D" },
  { id: "r32-3", round: "R32", team1Source: "1C", team2Source: "3A" },
  { id: "r32-4", round: "R32", team1Source: "1D", team2Source: "3B" },
  { id: "r32-5", round: "R32", team1Source: "1E", team2Source: "3G" },
  { id: "r32-6", round: "R32", team1Source: "1F", team2Source: "3H" },
  { id: "r32-7", round: "R32", team1Source: "1G", team2Source: "3E" },
  { id: "r32-8", round: "R32", team1Source: "1H", team2Source: "3F" },
  { id: "r32-9", round: "R32", team1Source: "2A", team2Source: "2D" },
  { id: "r32-10", round: "R32", team1Source: "2B", team2Source: "2C" },
  { id: "r32-11", round: "R32", team1Source: "2E", team2Source: "2H" },
  { id: "r32-12", round: "R32", team1Source: "2F", team2Source: "2G" },
  { id: "r32-13", round: "R32", team1Source: "1I", team2Source: "3K" },
  { id: "r32-14", round: "R32", team1Source: "1J", team2Source: "3L" },
  { id: "r32-15", round: "R32", team1Source: "1K", team2Source: "3I" },
  { id: "r32-16", round: "R32", team1Source: "1L", team2Source: "3J" },

  // Round of 16 (8 matches) — winners of R32 pairs
  { id: "r16-1", round: "R16", team1Source: "W:r32-1", team2Source: "W:r32-2" },
  { id: "r16-2", round: "R16", team1Source: "W:r32-3", team2Source: "W:r32-4" },
  { id: "r16-3", round: "R16", team1Source: "W:r32-5", team2Source: "W:r32-6" },
  { id: "r16-4", round: "R16", team1Source: "W:r32-7", team2Source: "W:r32-8" },
  { id: "r16-5", round: "R16", team1Source: "W:r32-9", team2Source: "W:r32-10" },
  { id: "r16-6", round: "R16", team1Source: "W:r32-11", team2Source: "W:r32-12" },
  { id: "r16-7", round: "R16", team1Source: "W:r32-13", team2Source: "W:r32-14" },
  { id: "r16-8", round: "R16", team1Source: "W:r32-15", team2Source: "W:r32-16" },

  // Quarter Finals (4 matches)
  { id: "qf-1", round: "QF", team1Source: "W:r16-1", team2Source: "W:r16-2" },
  { id: "qf-2", round: "QF", team1Source: "W:r16-3", team2Source: "W:r16-4" },
  { id: "qf-3", round: "QF", team1Source: "W:r16-5", team2Source: "W:r16-6" },
  { id: "qf-4", round: "QF", team1Source: "W:r16-7", team2Source: "W:r16-8" },

  // Semi Finals (2 matches)
  { id: "sf-1", round: "SF", team1Source: "W:qf-1", team2Source: "W:qf-2" },
  { id: "sf-2", round: "SF", team1Source: "W:qf-3", team2Source: "W:qf-4" },

  // Final
  { id: "final", round: "F", team1Source: "W:sf-1", team2Source: "W:sf-2" },
];

// Round display names
export const ROUND_NAMES: Record<string, string> = {
  R32: "Round of 32",
  R16: "Round of 16",
  QF: "Quarter Finals",
  SF: "Semi Finals",
  F: "Final",
};

// Resolve a bracket source to a team ID
export function resolveSource(
  source: string,
  groupStandings: Record<string, GroupStanding[]>,
  bracket: BracketMatch[]
): string | undefined {
  // "1A" → winner of group A
  if (/^[123][A-L]$/.test(source)) {
    const pos = parseInt(source[0]) - 1;
    const group = source[1];
    const standings = groupStandings[group];
    if (!standings || !standings[pos]) return undefined;
    return standings[pos].teamId;
  }

  // "W:r32-1" → winner of match r32-1
  if (source.startsWith("W:")) {
    const matchId = source.slice(2);
    const match = bracket.find((m) => m.id === matchId);
    return match?.winner;
  }

  return undefined;
}

// Estimate goals from probabilities (for group simulation)
export function estimateGoals(probs: {
  home_win: number;
  draw: number;
  away_win: number;
}): { homeGoals: number; awayGoals: number } {
  const rand = Math.random();
  if (rand < probs.home_win) {
    // Home win — generate a plausible scoreline
    const margin = Math.random() < 0.6 ? 1 : Math.random() < 0.8 ? 2 : 3;
    const awayGoals = Math.random() < 0.5 ? 0 : 1;
    return { homeGoals: awayGoals + margin, awayGoals };
  } else if (rand < probs.home_win + probs.draw) {
    // Draw
    const goals = Math.random() < 0.35 ? 0 : Math.random() < 0.7 ? 1 : 2;
    return { homeGoals: goals, awayGoals: goals };
  } else {
    // Away win
    const margin = Math.random() < 0.6 ? 1 : Math.random() < 0.8 ? 2 : 3;
    const homeGoals = Math.random() < 0.5 ? 0 : 1;
    return { homeGoals, awayGoals: homeGoals + margin };
  }
}
