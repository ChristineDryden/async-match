(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.Standings = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function filterMatchesByHours(matches, hours, nowMs) {
    var list = matches || [];
    if (hours == null) return list.slice();
    var now = nowMs == null ? Date.now() : nowMs;
    var cutoff = now - hours * 60 * 60 * 1000;
    return filterMatchesByRange(list, cutoff, now);
  }

  function filterMatchesByRange(matches, fromMs, toMs) {
    return (matches || []).filter(function (match) {
      if (!match || !match.date) return false;
      var ts = Date.parse(match.date);
      if (Number.isNaN(ts)) return false;
      if (fromMs != null && ts < fromMs) return false;
      if (toMs != null && ts > toMs) return false;
      return true;
    });
  }

  function recordSide(bucket, name, team, won, scored, allowed) {
    var row = bucket[name];
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

  function primaryTeam(stats) {
    var bestName = stats.lastTeam;
    var bestCount = -1;
    Object.keys(stats.teams).forEach(function (team) {
      var count = stats.teams[team];
      if (count > bestCount) {
        bestCount = count;
        bestName = team;
      }
    });
    if (bestName && stats.teams[bestName] === bestCount) {
      var tied = Object.keys(stats.teams).filter(function (team) {
        return stats.teams[team] === bestCount;
      });
      if (tied.length > 1) return stats.lastTeam;
    }
    return bestName;
  }

  function finishRows(bucket) {
    var rows = Object.keys(bucket).map(function (name) {
      var stats = bucket[name];
      var last5 = stats.results.slice(-5);
      var streakKind = stats.results.length ? stats.results[stats.results.length - 1] : "-";
      var streakN = 0;
      for (var i = stats.results.length - 1; i >= 0; i--) {
        if (stats.results[i] === streakKind) streakN += 1;
        else break;
      }
      var team = primaryTeam(stats);
      return {
        player: name,
        team: team,
        display: team + " (" + name + ")",
        p: stats.gp,
        w: stats.w,
        l: stats.l,
        pct: stats.gp ? stats.w / stats.gp : 0,
        pf: stats.pf,
        pa: stats.pa,
        l5: last5.filter(function (r) { return r === "W"; }).length + "-" +
          last5.filter(function (r) { return r === "L"; }).length,
        strk: streakN ? streakKind + " " + streakN : "-",
      };
    });

    rows.sort(function (a, b) {
      if (b.pct !== a.pct) return b.pct - a.pct;
      if (b.w !== a.w) return b.w - a.w;
      if (a.l !== b.l) return a.l - b.l;
      return b.pf - b.pa - (a.pf - a.pa);
    });

    if (rows.length) {
      var leader = rows[0];
      rows.forEach(function (row, index) {
        var gb = (leader.w - row.w + (row.l - leader.l)) / 2;
        row.rank = index + 1;
        row.wl = row.w + "-" + row.l;
        row.pctDisplay = row.pct.toFixed(3);
        row.winRate = (row.pct * 100).toFixed(1) + "%";
        row.gbDisplay = Math.abs(gb) < 1e-9 ? "-" : gb.toFixed(1);
      });
    }
    return rows;
  }

  function validMatches(matches) {
    var valid = (matches || []).filter(function (m) {
      return (
        m &&
        m.date &&
        m.home_player &&
        m.away_player &&
        m.home_team &&
        m.away_team &&
        m.home_score != null &&
        m.away_score != null
      );
    });
    valid.sort(function (a, b) {
      return Date.parse(a.date) - Date.parse(b.date);
    });
    return valid;
  }

  function computePlayerStandings(matches) {
    var players = {};
    validMatches(matches).forEach(function (match) {
      var homeWin = match.home_score > match.away_score;
      recordSide(
        players,
        match.home_player,
        match.home_team,
        homeWin,
        match.home_score,
        match.away_score
      );
      recordSide(
        players,
        match.away_player,
        match.away_team,
        !homeWin,
        match.away_score,
        match.home_score
      );
    });
    return finishRows(players).map(function (row) {
      return row;
    });
  }

  function computeTeamStandings(matches) {
    var teams = {};
    validMatches(matches).forEach(function (match) {
      var homeWin = match.home_score > match.away_score;
      recordSide(
        teams,
        match.home_team,
        match.home_player,
        homeWin,
        match.home_score,
        match.away_score
      );
      recordSide(
        teams,
        match.away_team,
        match.away_player,
        !homeWin,
        match.away_score,
        match.home_score
      );
    });
    return finishRows(teams).map(function (row) {
      var team = row.player;
      var player = row.team;
      return Object.assign({}, row, {
        team: team,
        player: player,
        display: team + " (" + player + ")",
      });
    });
  }

  function playerMatchLog(matches, playerName) {
    return validMatches(matches)
      .filter(function (match) {
        return match.home_player === playerName || match.away_player === playerName;
      })
      .sort(function (a, b) {
        return Date.parse(b.date) - Date.parse(a.date);
      })
      .map(function (match) {
        var isHome = match.home_player === playerName;
        var playerScore = isHome ? match.home_score : match.away_score;
        var opponentScore = isHome ? match.away_score : match.home_score;
        var won = playerScore > opponentScore;
        return {
          id: match.id,
          date: match.date,
          team: isHome ? match.home_team : match.away_team,
          opponent: isHome ? match.away_player : match.home_player,
          opponentTeam: isHome ? match.away_team : match.home_team,
          playerScore: playerScore,
          opponentScore: opponentScore,
          won: won,
          result: won ? "W" : "L",
        };
      });
  }

  function opponentRecords(log) {
    var bucket = {};
    (log || []).forEach(function (game) {
      var row = bucket[game.opponent];
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
      .map(function (name) {
        var row = bucket[name];
        var pct = row.p ? row.w / row.p : 0;
        return {
          opponent: row.opponent,
          p: row.p,
          w: row.w,
          l: row.l,
          wl: row.w + "-" + row.l,
          pct: pct,
          pctDisplay: pct.toFixed(3),
          winRate: (pct * 100).toFixed(1) + "%",
        };
      })
      .sort(function (a, b) {
        if (b.p !== a.p) return b.p - a.p;
        if (b.w !== a.w) return b.w - a.w;
        return a.opponent.localeCompare(b.opponent);
      });
  }

  return {
    filterMatchesByHours: filterMatchesByHours,
    filterMatchesByRange: filterMatchesByRange,
    computePlayerStandings: computePlayerStandings,
    computeTeamStandings: computeTeamStandings,
    playerMatchLog: playerMatchLog,
    opponentRecords: opponentRecords,
  };
});
