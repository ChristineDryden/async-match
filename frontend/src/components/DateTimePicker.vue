<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

const WEEK = ["日", "一", "二", "三", "四", "五", "六"];

const props = withDefaults(
  defineProps<{
    placeholder?: string;
    defaultHour?: number;
    defaultMinute?: number;
  }>(),
  {
    placeholder: "选择时间",
    defaultHour: 0,
    defaultMinute: 0,
  },
);

const value = defineModel<Date | null>({ default: null });

const host = ref<HTMLElement | null>(null);
const open = ref(false);
const view = ref(startOfDay(new Date()));
const draft = ref<Date | null>(null);

const hours = Array.from({ length: 24 }, (_, i) => i);
const minutes = Array.from({ length: 60 }, (_, i) => i);

function pad(n: number) {
  return String(n).padStart(2, "0");
}

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function sameDay(a: Date | null, b: Date | null) {
  return Boolean(
    a &&
      b &&
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate(),
  );
}

function formatValue(date: Date | null) {
  if (!date) return "";
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function cloneDate(date: Date | null) {
  return date ? new Date(date.getTime()) : null;
}

function buildCalendarDays(year: number, month: number) {
  const first = new Date(year, month, 1);
  const start = first.getDay();
  const days: Date[] = [];
  const cursor = new Date(year, month, 1 - start);
  for (let i = 0; i < 42; i++) {
    days.push(new Date(cursor.getTime()));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

function ensureDraft() {
  if (draft.value) return;
  if (value.value) {
    draft.value = cloneDate(value.value);
    return;
  }
  const next = new Date();
  next.setHours(props.defaultHour, props.defaultMinute, 0, 0);
  draft.value = next;
}

const label = computed(() =>
  value.value ? formatValue(value.value) : props.placeholder,
);

const calendarDays = computed(() =>
  buildCalendarDays(view.value.getFullYear(), view.value.getMonth()),
);

function close() {
  open.value = false;
}

function openPanel() {
  draft.value = cloneDate(value.value);
  view.value = startOfDay(value.value || new Date());
  open.value = true;
}

function toggle() {
  if (open.value) close();
  else openPanel();
}

function onNav(kind: string) {
  const next = new Date(view.value.getTime());
  if (kind === "prev-month") next.setMonth(next.getMonth() - 1);
  if (kind === "next-month") next.setMonth(next.getMonth() + 1);
  if (kind === "prev-year") next.setFullYear(next.getFullYear() - 1);
  if (kind === "next-year") next.setFullYear(next.getFullYear() + 1);
  view.value = next;
}

function pickDay(day: Date) {
  ensureDraft();
  const next = cloneDate(draft.value)!;
  next.setFullYear(day.getFullYear(), day.getMonth(), day.getDate());
  draft.value = next;
  view.value = startOfDay(next);
}

function pickHour(h: number) {
  ensureDraft();
  const next = cloneDate(draft.value)!;
  next.setHours(h);
  draft.value = next;
}

function pickMinute(m: number) {
  ensureDraft();
  const next = cloneDate(draft.value)!;
  next.setMinutes(m);
  draft.value = next;
}

function pickNow() {
  const next = new Date();
  draft.value = next;
  view.value = startOfDay(next);
}

function confirm() {
  ensureDraft();
  value.value = cloneDate(draft.value);
  close();
}

function onDocumentClick(event: MouseEvent) {
  if (!open.value) return;
  const target = event.target as Node | null;
  if (host.value && target && !host.value.contains(target)) close();
}

onMounted(() => document.addEventListener("click", onDocumentClick));
onUnmounted(() => document.removeEventListener("click", onDocumentClick));
</script>

<template>
  <div ref="host" class="dp">
    <button
      type="button"
      class="dp-trigger"
      :class="{ open }"
      aria-haspopup="dialog"
      @click="toggle"
    >
      <span class="dp-text" :class="{ 'dp-placeholder': !value }">{{ label }}</span>
      <span class="dp-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="3.5" y="5" width="17" height="15" rx="2" />
          <path d="M8 3.5v3M16 3.5v3M3.5 9.5h17" />
        </svg>
      </span>
    </button>
    <div v-show="open" class="dp-panel">
      <div class="dp-calendar">
        <div class="dp-head">
          <button type="button" class="dp-nav" aria-label="上一年" @click="onNav('prev-year')">«</button>
          <button type="button" class="dp-nav" aria-label="上个月" @click="onNav('prev-month')">‹</button>
          <div class="dp-title">{{ view.getFullYear() }}年 {{ view.getMonth() + 1 }}月</div>
          <button type="button" class="dp-nav" aria-label="下个月" @click="onNav('next-month')">›</button>
          <button type="button" class="dp-nav" aria-label="下一年" @click="onNav('next-year')">»</button>
        </div>
        <div class="dp-weeks">
          <span v-for="w in WEEK" :key="w">{{ w }}</span>
        </div>
        <div class="dp-grid">
          <button
            v-for="day in calendarDays"
            :key="day.toISOString()"
            type="button"
            class="dp-day"
            :class="{
              out: day.getMonth() !== view.getMonth(),
              today: sameDay(day, new Date()),
              selected: sameDay(day, draft),
            }"
            @click="pickDay(day)"
          >
            {{ day.getDate() }}
          </button>
        </div>
      </div>
      <div class="dp-time">
        <div class="dp-time-col">
          <button
            v-for="h in hours"
            :key="'h' + h"
            type="button"
            class="dp-time-item"
            :class="{ selected: draft && draft.getHours() === h }"
            @click="pickHour(h)"
          >
            {{ pad(h) }}
          </button>
        </div>
        <div class="dp-time-col">
          <button
            v-for="m in minutes"
            :key="'m' + m"
            type="button"
            class="dp-time-item"
            :class="{ selected: draft && draft.getMinutes() === m }"
            @click="pickMinute(m)"
          >
            {{ pad(m) }}
          </button>
        </div>
      </div>
      <div class="dp-foot">
        <button type="button" class="dp-now" @click="pickNow">此刻</button>
        <button type="button" class="dp-ok" @click="confirm">确定</button>
      </div>
    </div>
  </div>
</template>
