<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { fetchMatches } from "../api/matches";
import { formatTime } from "../lib/format";
import {
  computePlayerStandings,
  opponentRecords,
  playerMatchLog,
} from "../lib/standings";
import type { Match, OpponentRecord, PlayerGame } from "../types/match";

const route = useRoute();
const player = computed(() => String(route.query.name || ""));
const matches = ref<Match[]>([]);
const loadError = ref("");
const loaded = ref(false);

const log = computed<PlayerGame[]>(() =>
  player.value ? playerMatchLog(matches.value, player.value) : [],
);
const rivals = computed<OpponentRecord[]>(() => opponentRecords(log.value));
const self = computed(() =>
  computePlayerStandings(matches.value).find((row) => row.player === player.value),
);
const summary = computed(() => {
  if (self.value) {
    return `${self.value.display} · ${self.value.p} 场 · ${self.value.wl} · ${self.value.pctDisplay}`;
  }
  return `${log.value.length} 场对战记录`;
});

watch(
  player,
  (name) => {
    document.title = name ? `${name} · 对战记录` : "选手对战记录";
  },
  { immediate: true },
);

onMounted(async () => {
  if (!player.value) {
    loaded.value = true;
    return;
  }
  try {
    const data = await fetchMatches();
    matches.value = data.matches || [];
  } catch (err) {
    loadError.value = String(err);
  } finally {
    loaded.value = true;
  }
});
</script>

<template>
  <div class="wrap">
    <router-link class="back" to="/">← 返回积分榜</router-link>
    <div class="kicker">
      <h1>{{ player || "未指定选手" }}</h1>
      <div class="sub">{{ player ? summary : "" }}</div>
    </div>

    <p v-if="!player" class="error">缺少选手名称。</p>
    <p v-else-if="loadError" class="error">无法读取比赛数据。</p>
    <template v-else-if="loaded">
      <section class="section">
        <h2>对战过的选手</h2>
        <p v-if="!rivals.length" class="empty">还没有对战记录。</p>
        <table v-else class="board">
          <thead>
            <tr>
              <th>#</th>
              <th class="name-h">对手</th>
              <th>P</th>
              <th>W-L</th>
              <th>PCT</th>
              <th>胜率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in rivals" :key="row.opponent">
              <td><div class="rank">{{ i + 1 }}</div></td>
              <td>
                <div class="name">
                  <router-link :to="{ name: 'player', query: { name: row.opponent } }">
                    {{ row.opponent }}
                  </router-link>
                </div>
              </td>
              <td><div class="stat">{{ row.p }}</div></td>
              <td><div class="stat">{{ row.wl }}</div></td>
              <td><div class="stat">{{ row.pctDisplay }}</div></td>
              <td><div class="stat">{{ row.winRate }}</div></td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="section">
        <h2>比赛明细</h2>
        <p v-if="!log.length" class="empty">没有找到该选手的比赛。</p>
        <article v-for="game in log" :key="game.id" class="game player-game">
          <div class="side" :class="game.won ? 'winner' : 'loser'">
            <div class="pname">{{ player }}</div>
            <div class="tname">{{ game.team }}</div>
          </div>
          <div>
            <div class="score">{{ game.playerScore }} – {{ game.opponentScore }}</div>
            <div class="mid">{{ formatTime(game.date) }} · #{{ game.id }}</div>
          </div>
          <div class="side away" :class="game.won ? 'loser' : 'winner'">
            <div class="pname">
              <router-link :to="{ name: 'player', query: { name: game.opponent } }">
                {{ game.opponent }}
              </router-link>
            </div>
            <div class="tname">{{ game.opponentTeam }}</div>
          </div>
          <div class="badge" :class="game.result">{{ game.result }}</div>
        </article>
      </section>
    </template>
  </div>
</template>
