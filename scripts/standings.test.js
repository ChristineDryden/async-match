const assert = require("assert");
const { filterMatchesByHours, computePlayerStandings } = require("../js/standings.js");

const now = Date.parse("2026-10-15T08:00:00.000Z");

const matches = [
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

function byPlayer(rows, name) {
  return rows.find((row) => row.player === name);
}

{
  const recent = filterMatchesByHours(matches, 3, now);
  assert.deepStrictEqual(
    recent.map((m) => m.id),
    ["1"],
    "3h keeps only matches in the last 3 hours"
  );
}

{
  const recent = filterMatchesByHours(matches, 6, now);
  assert.deepStrictEqual(
    recent.map((m) => m.id).sort(),
    ["1", "2"],
    "6h keeps matches in the last 6 hours"
  );
}

{
  const recent = filterMatchesByHours(matches, 12, now);
  assert.deepStrictEqual(
    recent.map((m) => m.id).sort(),
    ["1", "2"],
    "12h still excludes a match from the previous day"
  );
}

{
  const recent = filterMatchesByHours(matches, null, now);
  assert.strictEqual(recent.length, 3, "all keeps every match");
}

{
  const rows = computePlayerStandings(matches);
  const melo = byPlayer(rows, "Melo");
  assert.ok(melo, "Melo is on the player table");
  assert.strictEqual(melo.p, 2);
  assert.strictEqual(melo.wl, "2-0");
  assert.strictEqual(melo.pctDisplay, "1.000");
  assert.strictEqual(melo.winRate, "100.0%");
  assert.strictEqual(melo.gbDisplay, "-");
  assert.strictEqual(melo.l5, "2-0");
  assert.strictEqual(melo.strk, "W 2");
  assert.strictEqual(melo.display, "Los Angeles Lakers (Melo)");
  assert.strictEqual(melo.rank, 1);
}

{
  const rows = computePlayerStandings(matches);
  const ray = byPlayer(rows, "Ray");
  assert.strictEqual(ray.p, 2);
  assert.strictEqual(ray.wl, "0-2");
  assert.strictEqual(ray.pctDisplay, "0.000");
  assert.strictEqual(ray.gbDisplay, "2.0");
  assert.strictEqual(ray.l5, "0-2");
  assert.strictEqual(ray.strk, "L 2");
}

{
  const rows = computePlayerStandings(
    filterMatchesByHours(matches, 3, now)
  );
  assert.strictEqual(rows.length, 2);
  assert.strictEqual(byPlayer(rows, "Melo").wl, "1-0");
  assert.strictEqual(byPlayer(rows, "Ray").wl, "0-1");
  assert.strictEqual(byPlayer(rows, "Jason"), undefined);
}

{
  const rows = computePlayerStandings([]);
  assert.deepStrictEqual(rows, []);
}

{
  const { computeTeamStandings } = require("../js/standings.js");
  const rows = computeTeamStandings(matches);
  const lakers = rows.find((row) => row.team === "Los Angeles Lakers");
  assert.strictEqual(lakers.wl, "1-0");
  assert.strictEqual(lakers.display, "Los Angeles Lakers (Melo)");
}

{
  const { filterMatchesByRange } = require("../js/standings.js");
  const from = Date.parse("2026-10-15T04:00:00.000Z");
  const to = Date.parse("2026-10-15T07:30:00.000Z");
  const got = filterMatchesByRange(matches, from, to).map((m) => m.id).sort();
  assert.deepStrictEqual(got, ["1", "2"], "custom range is inclusive");
}

{
  const { filterMatchesByRange } = require("../js/standings.js");
  const from = Date.parse("2026-10-15T06:00:00.000Z");
  const got = filterMatchesByRange(matches, from, null).map((m) => m.id);
  assert.deepStrictEqual(got, ["1"], "open-ended range uses only the start");
}

{
  const { playerMatchLog } = require("../js/standings.js");
  const log = playerMatchLog(matches, "Melo");
  assert.strictEqual(log.length, 2);
  assert.strictEqual(log[0].opponent, "Ray");
  assert.strictEqual(log[0].won, true);
  assert.strictEqual(log[0].playerScore, 90);
  assert.strictEqual(log[0].opponentScore, 70);
  assert.strictEqual(log[1].opponent, "Jason");
  assert.strictEqual(log[1].result, "W");
}

{
  const { playerMatchLog, opponentRecords } = require("../js/standings.js");
  const rows = opponentRecords(playerMatchLog(matches, "Jason"));
  const vsMelo = rows.find((row) => row.opponent === "Melo");
  const vsRay = rows.find((row) => row.opponent === "Ray");
  assert.strictEqual(vsMelo.wl, "0-1");
  assert.strictEqual(vsRay.wl, "1-0");
}

console.log("ok");
