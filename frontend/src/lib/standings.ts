import type {
  Match,
  OpponentRecord,
  PlayerGame,
  StandingRow,
} from "../types/match";

type ResultMark = "W" | "L";

interface SideStats {
  gp: number;
  w: number;
  l: number;
  pf: number;
  pa: number;
  results: ResultMark[];
  teams: Record<string, number>;
  lastTeam: string;
}

export function filterMatchesByRange(
  matches: Match[] | null | undefined,
  fromMs: number | null,
  toMs: number | null,
): Match[] {
  return (matches || []).filter((match) => {
    if (!match || !match.date) return false;
    const ts = Date.parse(match.date);
    if (Number.isNaN(ts)) return false;
    if (fromMs != null && ts < fromMs) return false;
    if (toMs != null && ts > toMs) return false;
    return true;
  });
}

export function filterMatchesByHours(
  matches: Match[] | null | undefined,
  hours: number | null,
  nowMs?: number,
): Match[] {
  const list = matches || [];
  if (hours == null) return list.slice();
  const now = nowMs == null ? Date.now() : nowMs;
  const cutoff = now - hours * 60 * 60 * 1000;
  return filterMatchesByRange(list, cutoff, now);
}

function recordSide(
  bucket: Record<string, SideStats>,
  name: string,
  team: string,
  won: boolean,
  scored: number,
  allowed: number,
) {
  let row = bucket[name];
  if (!row) {
    row = bucket[name] = {
      gp: 0,
      w: 0,
      l: 0,
      pf: 0,
      pa: 0,
      results: [],
      teams: {},
      lastTeam: team,
    };
  }
  row.gp += 1;
  if (won) row.w += 1;
  else row.l += 1;
  row.pf += scored;
  row.pa += allowed;
  row.results.push(won ? "W" : "L");
  row.teams[team] = (row.teams[team] || 0) + 1;
  row.lastTeam = team;
}

function primaryTeam(stats: SideStats): string {
  let bestName = stats.lastTeam;
  let bestCount = -1;
  Object.keys(stats.teams).forEach((team) => {
    const count = stats.teams[team];
    if (count > bestCount) {
      bestCount = count;
      bestName = team;
    }
  });
  if (bestName && stats.teams[bestName] === bestCount) {
    const tied = Object.keys(stats.teams).filter(
      (team) => stats.teams[team] === bestCount,
    );
    if (tied.length > 1) return stats.lastTeam;
  }
  return bestName;
}

function finishRows(bucket: Record<string, SideStats>): StandingRow[] {
  const rows: StandingRow[] = Object.keys(bucket).map((name) => {
    const stats = bucket[name];
    const last5 = stats.results.slice(-5);
    const streakKind: ResultMark | "-" = stats.results.length
      ? stats.results[stats.results.length - 1]
      : "-";
    let streakN = 0;
    for (let i = stats.results.length - 1; i >= 0; i--) {
      if (stats.results[i] === streakKind) streakN += 1;
      else break;
    }
    const team = primaryTeam(stats);
    return {
      player: name,
      team,
      display: `${team} (${name})`,
      p: stats.gp,
      w: stats.w,
      l: stats.l,
      pct: stats.gp ? stats.w / stats.gp : 0,
      pf: stats.pf,
      pa: stats.pa,
      l5:
        last5.filter((r) => r === "W").length +
        "-" +
        last5.filter((r) => r === "L").length,
      strk: streakN ? `${streakKind} ${streakN}` : "-",
      rank: 0,
      wl: "",
      pctDisplay: "",
      winRate: "",
      gbDisplay: "",
    };
  });

  rows.sort((a, b) => {
    if (b.pct !== a.pct) return b.pct - a.pct;
    if (b.w !== a.w) return b.w - a.w;
    if (a.l !== b.l) return a.l - b.l;
    return b.pf - b.pa - (a.pf - a.pa);
  });

  if (rows.length) {
    const leader = rows[0];
    rows.forEach((row, index) => {
      const gb = (leader.w - row.w + (row.l - leader.l)) / 2;
      row.rank = index + 1;
      row.wl = `${row.w}-${row.l}`;
      row.pctDisplay = row.pct.toFixed(3);
      row.winRate = `${(row.pct * 100).toFixed(1)}%`;
      row.gbDisplay = Math.abs(gb) < 1e-9 ? "-" : gb.toFixed(1);
    });
  }
  return rows;
}

export function validMatches(matches: Match[] | null | undefined): Match[] {
  const valid = (matches || []).filter(
    (m) =>
      m &&
      m.date &&
      m.home_player &&
      m.away_player &&
      m.home_team &&
      m.away_team &&
      m.home_score != null &&
      m.away_score != null,
  );
  valid.sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
  return valid;
}

export function computePlayerStandings(
  matches: Match[] | null | undefined,
): StandingRow[] {
  const players: Record<string, SideStats> = {};
  validMatches(matches).forEach((match) => {
    const homeWin = match.home_score > match.away_score;
    recordSide(
      players,
      match.home_player,
      match.home_team,
      homeWin,
      match.home_score,
      match.away_score,
    );
    recordSide(
      players,
      match.away_player,
      match.away_team,
      !homeWin,
      match.away_score,
      match.home_score,
    );
  });
  return finishRows(players);
}

export function computeTeamStandings(
  matches: Match[] | null | undefined,
): StandingRow[] {
  const teams: Record<string, SideStats> = {};
  validMatches(matches).forEach((match) => {
    const homeWin = match.home_score > match.away_score;
    recordSide(
      teams,
      match.home_team,
      match.home_player,
      homeWin,
      match.home_score,
      match.away_score,
    );
    recordSide(
      teams,
      match.away_team,
      match.away_player,
      !homeWin,
      match.away_score,
      match.home_score,
    );
  });
  return finishRows(teams).map((row) => {
    const team = row.player;
    const player = row.team;
    return {
      ...row,
      team,
      player,
      display: `${team} (${player})`,
    };
  });
}

export function playerMatchLog(
  matches: Match[] | null | undefined,
  playerName: string,
): PlayerGame[] {
  return validMatches(matches)
    .filter(
      (match) =>
        match.home_player === playerName || match.away_player === playerName,
    )
    .sort((a, b) => Date.parse(b.date) - Date.parse(a.date))
    .map((match) => {
      const isHome = match.home_player === playerName;
      const playerScore = isHome ? match.home_score : match.away_score;
      const opponentScore = isHome ? match.away_score : match.home_score;
      const won = playerScore > opponentScore;
      return {
        id: match.id,
        date: match.date,
        team: isHome ? match.home_team : match.away_team,
        opponent: isHome ? match.away_player : match.home_player,
        opponentTeam: isHome ? match.away_team : match.home_team,
        playerScore,
        opponentScore,
        won,
        result: won ? "W" : "L",
      };
    });
}

export function opponentRecords(log: PlayerGame[] | null | undefined): OpponentRecord[] {
  const bucket: Record<
    string,
    { opponent: string; p: number; w: number; l: number }
  > = {};
  (log || []).forEach((game) => {
    let row = bucket[game.opponent];
    if (!row) {
      row = bucket[game.opponent] = {
        opponent: game.opponent,
        p: 0,
        w: 0,
        l: 0,
      };
    }
    row.p += 1;
    if (game.won) row.w += 1;
    else row.l += 1;
  });
  return Object.keys(bucket)
    .map((name) => {
      const row = bucket[name];
      const pct = row.p ? row.w / row.p : 0;
      return {
        opponent: row.opponent,
        p: row.p,
        w: row.w,
        l: row.l,
        wl: `${row.w}-${row.l}`,
        pct,
        pctDisplay: pct.toFixed(3),
        winRate: `${(pct * 100).toFixed(1)}%`,
      };
    })
    .sort((a, b) => {
      if (b.p !== a.p) return b.p - a.p;
      if (b.w !== a.w) return b.w - a.w;
      return a.opponent.localeCompare(b.opponent);
    });
}
