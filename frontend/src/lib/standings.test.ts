import { describe, expect, it } from "vitest";
import {
  computePlayerStandings,
  computeTeamStandings,
  filterMatchesByHours,
  filterMatchesByRange,
  opponentRecords,
  playerMatchLog,
} from "./standings";
import type { Match, StandingRow } from "../types/match";

const now = Date.parse("2026-10-15T08:00:00.000Z");

const matches: Match[] = [
  {
    id: "1",
    date: "2026-10-15T07:30:00.000Z",
    home_player: "Melo",
    away_player: "Ray",
    home_team: "Los Angeles Lakers",
    away_team: "New York Knicks",
    home_score: 90,
    away_score: 70,
  },
  {
    id: "2",
    date: "2026-10-15T04:00:00.000Z",
    home_player: "Melo",
    away_player: "Jason",
    home_team: "Denver Nuggets",
    away_team: "Brooklyn Nets",
    home_score: 80,
    away_score: 75,
  },
  {
    id: "3",
    date: "2026-10-14T12:00:00.000Z",
    home_player: "Ray",
    away_player: "Jason",
    home_team: "Dallas Mavericks",
    away_team: "Brooklyn Nets",
    home_score: 60,
    away_score: 88,
  },
];

function byPlayer(rows: StandingRow[], name: string) {
  return rows.find((row) => row.player === name);
}

describe("filterMatchesByHours", () => {
  it("3h keeps only matches in the last 3 hours", () => {
    expect(filterMatchesByHours(matches, 3, now).map((m) => m.id)).toEqual(["1"]);
  });

  it("6h keeps matches in the last 6 hours", () => {
    expect(
      filterMatchesByHours(matches, 6, now)
        .map((m) => m.id)
        .sort(),
    ).toEqual(["1", "2"]);
  });

  it("12h still excludes a match from the previous day", () => {
    expect(
      filterMatchesByHours(matches, 12, now)
        .map((m) => m.id)
        .sort(),
    ).toEqual(["1", "2"]);
  });

  it("all keeps every match", () => {
    expect(filterMatchesByHours(matches, null, now)).toHaveLength(3);
  });
});

describe("computePlayerStandings", () => {
  it("ranks Melo as undefeated leader", () => {
    const melo = byPlayer(computePlayerStandings(matches), "Melo");
    expect(melo).toBeTruthy();
    expect(melo?.p).toBe(2);
    expect(melo?.wl).toBe("2-0");
    expect(melo?.pctDisplay).toBe("1.000");
    expect(melo?.winRate).toBe("100.0%");
    expect(melo?.gbDisplay).toBe("-");
    expect(melo?.l5).toBe("2-0");
    expect(melo?.strk).toBe("W 2");
    expect(melo?.display).toBe("Los Angeles Lakers (Melo)");
    expect(melo?.rank).toBe(1);
  });

  it("puts Ray at 0-2", () => {
    const ray = byPlayer(computePlayerStandings(matches), "Ray");
    expect(ray?.p).toBe(2);
    expect(ray?.wl).toBe("0-2");
    expect(ray?.pctDisplay).toBe("0.000");
    expect(ray?.gbDisplay).toBe("2.0");
    expect(ray?.l5).toBe("0-2");
    expect(ray?.strk).toBe("L 2");
  });

  it("filters 3h window onto two players", () => {
    const rows = computePlayerStandings(filterMatchesByHours(matches, 3, now));
    expect(rows).toHaveLength(2);
    expect(byPlayer(rows, "Melo")?.wl).toBe("1-0");
    expect(byPlayer(rows, "Ray")?.wl).toBe("0-1");
    expect(byPlayer(rows, "Jason")).toBeUndefined();
  });

  it("returns empty for no matches", () => {
    expect(computePlayerStandings([])).toEqual([]);
  });
});

describe("computeTeamStandings", () => {
  it("keeps Lakers as Melo's team", () => {
    const lakers = computeTeamStandings(matches).find(
      (row) => row.team === "Los Angeles Lakers",
    );
    expect(lakers?.wl).toBe("1-0");
    expect(lakers?.display).toBe("Los Angeles Lakers (Melo)");
  });
});

describe("filterMatchesByRange", () => {
  it("custom range is inclusive", () => {
    const from = Date.parse("2026-10-15T04:00:00.000Z");
    const to = Date.parse("2026-10-15T07:30:00.000Z");
    expect(
      filterMatchesByRange(matches, from, to)
        .map((m) => m.id)
        .sort(),
    ).toEqual(["1", "2"]);
  });

  it("open-ended range uses only the start", () => {
    const from = Date.parse("2026-10-15T06:00:00.000Z");
    expect(filterMatchesByRange(matches, from, null).map((m) => m.id)).toEqual([
      "1",
    ]);
  });
});

describe("player records", () => {
  it("builds Melo match log newest first", () => {
    const log = playerMatchLog(matches, "Melo");
    expect(log).toHaveLength(2);
    expect(log[0].opponent).toBe("Ray");
    expect(log[0].won).toBe(true);
    expect(log[0].playerScore).toBe(90);
    expect(log[0].opponentScore).toBe(70);
    expect(log[1].opponent).toBe("Jason");
    expect(log[1].result).toBe("W");
  });

  it("summarizes Jason opponent records", () => {
    const rows = opponentRecords(playerMatchLog(matches, "Jason"));
    const vsMelo = rows.find((row) => row.opponent === "Melo");
    const vsRay = rows.find((row) => row.opponent === "Ray");
    expect(vsMelo?.wl).toBe("0-1");
    expect(vsRay?.wl).toBe("1-0");
  });
});
