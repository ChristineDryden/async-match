<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import DateTimePicker from "../components/DateTimePicker.vue";
import GameList from "../components/GameList.vue";
import StandingsTable from "../components/StandingsTable.vue";
import { fetchMatches, syncMatches } from "../api/matches";
import { formatDate, formatTime } from "../lib/format";
import {
  computePlayerStandings,
  computeTeamStandings,
  filterMatchesByHours,
  filterMatchesByRange,
} from "../lib/standings";
import type { Match } from "../types/match";

type Mode = "team" | "player";

const matches = ref<Match[]>([]);
const count = ref(0);
const loadError = ref("");
const mode = ref<Mode>("player");
const hours = ref<number | null>(null);
const rangeFrom = ref<Date | null>(null);
const rangeTo = ref<Date | null>(null);
const rangeFromMs = ref<number | null>(null);
const rangeToMs = ref<number | null>(null);
const syncing = ref(false);
const syncStatus = ref("");

const filtered = computed(() => {
  let list = matches.value;
  if (hours.value) {
    list = filterMatchesByHours(list, hours.value);
  } else if (rangeFromMs.value != null || rangeToMs.value != null) {
    list = filterMatchesByRange(list, rangeFromMs.value, rangeToMs.value);
  }
  return list;
});

const rows = computed(() =>
  mode.value === "team"
    ? computeTeamStandings(filtered.value)
    : computePlayerStandings(filtered.value),
);

const recentGames = computed(() =>
  filtered.value
    .slice()
    .sort((a, b) => Date.parse(b.date) - Date.parse(a.date))
    .slice(0, 24),
);

const windowLabel = computed(() => {
  if (hours.value) return `最近 ${hours.value} 小时`;
  if (rangeFromMs.value != null || rangeToMs.value != null) return "自定义区间";
  return "全部数据";
});

const headline = computed(() => {
  const dates = matches.value.map((m) => m.date).filter(Boolean);
  const last = dates.length ? dates[0] : null;
  return `Valhalla League Basketball  ${formatDate(last)}`;
});

const meta = computed(() => {
  const dates = matches.value.map((m) => m.date).filter(Boolean);
  const first = dates.length ? dates[dates.length - 1] : null;
  const last = dates.length ? dates[0] : null;
  return `${count.value} 场已入库  ·  ${formatDate(first)} – ${formatDate(last)}  ·  MySQL`;
});

const countText = computed(
  () =>
    `${windowLabel.value} · ${filtered.value.length} 场 · 按${mode.value === "team" ? "球队" : "选手"}统计`,
);

async function load() {
  const data = await fetchMatches();
  matches.value = data.matches || [];
  count.value = data.count || 0;
}

function setMode(next: Mode) {
  mode.value = next;
}

function setHours(next: number | null, lockPlayer: boolean) {
  hours.value = next;
  rangeFrom.value = null;
  rangeTo.value = null;
  rangeFromMs.value = null;
  rangeToMs.value = null;
  if (lockPlayer) mode.value = "player";
}

function applyRange() {
  const fromMs = rangeFrom.value ? rangeFrom.value.getTime() : null;
  const toMs = rangeTo.value ? rangeTo.value.getTime() : null;
  if (fromMs == null && toMs == null) return;
  hours.value = null;
  rangeFromMs.value = fromMs;
  rangeToMs.value = toMs;
  mode.value = "player";
}

async function onSync() {
  syncing.value = true;
  syncStatus.value = "正在从 drafted.gg 增量同步…";
  try {
    const result = await syncMatches();
    await load();
    const from = result.watermark ? "从 " + formatTime(result.watermark) : "空库全量";
    syncStatus.value = `${from} · 新增 ${result.inserted} · 已存在跳过 ${result.skipped} · 库内 ${result.total} 场`;
  } catch (err) {
    syncStatus.value = "同步失败：" + err;
  } finally {
    syncing.value = false;
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  const target = event.target as HTMLElement | null;
  const tag = target?.tagName || "";
  if (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "BUTTON" ||
    target?.isContentEditable ||
    target?.closest(".dp")
  ) {
    return;
  }
  if (event.key === "1") setHours(3, true);
  if (event.key === "2") setHours(6, true);
  if (event.key === "3") setHours(12, true);
  if (event.key === "0") setHours(null, false);
}

onMounted(async () => {
  document.addEventListener("keydown", onKeydown);
  try {
    await load();
  } catch (err) {
    loadError.value = String(err);
  }
});

onUnmounted(() => {
  document.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <div class="wrap">
    <div class="kicker">
      <div class="kicker-title">
        <span class="dot"></span>
        <span>{{ headline }}</span>
      </div>
      <div class="meta">{{ loadError ? "Loading failed" : meta }}</div>
    </div>

    <div class="toolbar">
      <div class="filters">
        <div class="tabs">
          <button type="button" :class="{ active: mode === 'team' }" @click="setMode('team')">
            球队积分榜
          </button>
          <button type="button" :class="{ active: mode === 'player' }" @click="setMode('player')">
            选手积分榜
          </button>
        </div>
        <div class="tabs">
          <button type="button" :class="{ active: hours == null }" @click="setHours(null, false)">
            全部 <kbd>0</kbd>
          </button>
          <button type="button" :class="{ active: hours === 3 }" @click="setHours(3, true)">
            3h <kbd>1</kbd>
          </button>
          <button type="button" :class="{ active: hours === 6 }" @click="setHours(6, true)">
            6h <kbd>2</kbd>
          </button>
          <button type="button" :class="{ active: hours === 12 }" @click="setHours(12, true)">
            12h <kbd>3</kbd>
          </button>
        </div>
      </div>
      <div class="meta">{{ countText }}</div>
    </div>

    <div class="range">
      <label>从</label>
      <DateTimePicker v-model="rangeFrom" placeholder="开始时间" :default-hour="0" :default-minute="0" />
      <label>到</label>
      <DateTimePicker v-model="rangeTo" placeholder="结束时间" :default-hour="23" :default-minute="59" />
      <button type="button" class="action" @click="applyRange">应用区间</button>
      <button type="button" class="action" @click="setHours(null, false)">清除区间</button>
      <button type="button" class="action primary" :disabled="syncing" @click="onSync">一键同步</button>
      <span class="meta">{{ syncStatus }}</span>
    </div>
    <p class="hint">
      快捷键：1 = 最近 3 小时，2 = 最近 6 小时，3 = 最近 12 小时，0 = 全部。也可自定义起止时间。同步只入库新场次，并从库内最新比赛时间点接着爬。
    </p>

    <p v-if="loadError" class="error">
      无法读取数据库比赛数据。请运行 python3 -m server.app 后刷新。<br />{{ loadError }}
    </p>
    <StandingsTable v-else-if="rows.length" :rows="rows" />
    <p v-else class="empty">该时间窗口内没有篮球比赛，换一个时间范围或点同步。</p>

    <section class="results">
      <h2>近期篮球赛果</h2>
      <GameList :matches="recentGames" />
    </section>
  </div>
</template>
