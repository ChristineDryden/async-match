<script setup lang="ts">
import type { StandingRow } from "../types/match";
import { streakClass } from "../lib/format";

defineProps<{
  rows: StandingRow[];
}>();
</script>

<template>
  <table class="board">
    <thead>
      <tr>
        <th>#</th>
        <th class="team-h"></th>
        <th>P</th>
        <th>W-L</th>
        <th>PCT</th>
        <th>胜率</th>
        <th>GB</th>
        <th>L5</th>
        <th>STRK</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in rows" :key="row.display + row.rank">
        <td><div class="rank">{{ row.rank }}</div></td>
        <td>
          <div class="team">{{ row.team }} (<router-link class="player-link" :to="{ name: 'player', query: { name: row.player } }">{{ row.player }}</router-link>)</div>
        </td>
        <td><div class="stat">{{ row.p }}</div></td>
        <td><div class="stat">{{ row.wl }}</div></td>
        <td><div class="stat">{{ row.pctDisplay }}</div></td>
        <td><div class="stat">{{ row.winRate }}</div></td>
        <td><div class="stat">{{ row.gbDisplay }}</div></td>
        <td><div class="stat">{{ row.l5 }}</div></td>
        <td><div class="stat" :class="streakClass(row.strk)">{{ row.strk }}</div></td>
      </tr>
    </tbody>
  </table>
</template>
