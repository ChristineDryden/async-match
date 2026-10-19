<script setup lang="ts">
import type { Match } from "../types/match";
import { formatTime } from "../lib/format";

defineProps<{
  matches: Match[];
}>();
</script>

<template>
  <p v-if="!matches.length" class="empty">该时间窗口内没有篮球比赛。</p>
  <article v-for="m in matches" :key="m.id" class="game">
    <div class="side" :class="m.home_score > m.away_score ? 'winner' : 'loser'">
      <div class="pname">{{ m.home_player }}</div>
      <div class="tname">{{ m.home_team }}</div>
    </div>
    <div class="scorebox">
      <div class="score">{{ m.home_score }} – {{ m.away_score }}</div>
      <div class="mid">{{ formatTime(m.date) }} · #{{ m.id }}</div>
    </div>
    <div class="side away" :class="m.home_score > m.away_score ? 'loser' : 'winner'">
      <div class="pname">{{ m.away_player }}</div>
      <div class="tname">{{ m.away_team }}</div>
    </div>
  </article>
</template>
