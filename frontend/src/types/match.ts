export interface Match {
  id: string;
  date: string;
  home_player: string;
  away_player: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  period_type?: string | null;
}

export interface MatchesResponse {
  matches: Match[];
  count: number;
  latest: string | null;
}

export interface SyncResponse {
  watermark: string | null;
  scanned: number;
  inserted: number;
  skipped: number;
  latest: string | null;
  total: number;
}

export interface StandingRow {
  player: string;
  team: string;
  display: string;
  p: number;
  w: number;
  l: number;
  pct: number;
  pf: number;
  pa: number;
  l5: string;
  strk: string;
  rank: number;
  wl: string;
  pctDisplay: string;
  winRate: string;
  gbDisplay: string;
}

export interface PlayerGame {
  id: string;
  date: string;
  team: string;
  opponent: string;
  opponentTeam: string;
  playerScore: number;
  opponentScore: number;
  won: boolean;
  result: "W" | "L";
}

export interface OpponentRecord {
  opponent: string;
  p: number;
  w: number;
  l: number;
  wl: string;
  pct: number;
  pctDisplay: string;
  winRate: string;
}
