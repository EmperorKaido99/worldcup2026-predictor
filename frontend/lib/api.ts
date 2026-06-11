const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Team {
  id: string;
  name: string;
}

export interface PredictMatchRequest {
  home: string;
  away: string;
  neutral: boolean;
}

export interface PredictMatchResponse {
  home: string;
  away: string;
  neutral: boolean;
  probabilities: {
    home_win: number;
    draw: number;
    away_win: number;
  };
  context: {
    elo_home: number;
    elo_away: number;
    form_home: string;
    form_away: string;
  };
}

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 60000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `API error: ${res.status}`);
    }
    return res.json();
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(
        "Request timed out. The API may be cold-starting (free tier takes ~30-50s). Please try again."
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function getTeams(): Promise<Team[]> {
  const data = await fetchWithTimeout(`${API_URL}/teams`);
  return data.teams;
}

export async function predictMatch(
  req: PredictMatchRequest
): Promise<PredictMatchResponse> {
  return fetchWithTimeout(`${API_URL}/predict-match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

// --- xG API (P1) ---

export interface XgStats {
  team: string;
  total_shots: number;
  goals: number;
  total_xg: number;
  xg_per_shot: number;
  conversion_rate: number;
  top_scorers: { player: string; goals: number }[];
}

export async function getXgStats(teamId: string): Promise<XgStats> {
  return fetchWithTimeout(`${API_URL}/xg/team/${teamId}`);
}

export function getXgShotMapUrl(teamId: string): string {
  return `${API_URL}/xg/team/${teamId}/shotmap`;
}

export function getXgHeatmapUrl(teamId: string): string {
  return `${API_URL}/xg/team/${teamId}/heatmap`;
}
