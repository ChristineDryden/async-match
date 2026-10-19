<script setup lang="ts">
import { nextTick, ref } from "vue";
import { sendChat } from "../api/chat";
import { formatChatHtml } from "../lib/format";

interface Bubble {
  role: "user" | "assistant";
  text: string;
  tools?: string[];
  error?: boolean;
}

interface PromptItem {
  key: string;
  label: string;
  description: string;
  ask: string;
}

const TOOL_LABELS: Record<string, string> = {
  get_league_summary: "联赛总览",
  get_player_standings: "选手积分榜",
  get_team_standings: "球队积分榜",
  get_player_record: "选手战绩",
  get_head_to_head: "交锋记录",
  get_recent_matches: "最近赛果",
  search_players: "搜索选手",
};

const PROMPTS: PromptItem[] = [
  {
    key: "lead",
    label: "当前领先者",
    description: "谁在选手榜第一，胜率和连胜如何？",
    ask: "现在谁领先？",
  },
  {
    key: "window",
    label: "近 6 小时",
    description: "最近窗口里形势有没有变化？",
    ask: "最近 6 小时什么形势？",
  },
  {
    key: "melo",
    label: "Melo 近况",
    description: "战绩、主要对手和最近几场比分。",
    ask: "Melo 近况怎么样？",
  },
  {
    key: "predict",
    label: "对战胜率",
    description: "用 Elo 估计 Melo 对阵 Ray 谁更可能赢。",
    ask: "预测 Melo 对战 Ray 的获胜概率",
  },
];

const open = ref(false);
const input = ref("");
const loading = ref(false);
const messages = ref<Bubble[]>([]);
const scroller = ref<HTMLElement | null>(null);

async function scrollToEnd() {
  await nextTick();
  const el = scroller.value;
  if (el) el.scrollTop = el.scrollHeight;
}

function toggle() {
  open.value = !open.value;
  if (open.value) scrollToEnd();
}

function reset() {
  messages.value = [];
  input.value = "";
}

function toolLabel(name: string) {
  return TOOL_LABELS[name] || name;
}

async function ask(text: string) {
  const content = text.trim();
  if (!content || loading.value) return;
  input.value = "";
  messages.value.push({ role: "user", text: content });
  loading.value = true;
  await scrollToEnd();
  try {
    const data = await sendChat(
      messages.value.map((msg) => ({ role: msg.role, content: msg.text })),
    );
    messages.value.push({
      role: "assistant",
      text: data.reply,
      tools: data.tools_used,
    });
  } catch (err) {
    messages.value.push({
      role: "assistant",
      text: err instanceof Error ? err.message : String(err),
      error: true,
    });
  } finally {
    loading.value = false;
    await scrollToEnd();
  }
}

function onSubmit(event: Event) {
  event.preventDefault();
  void ask(input.value);
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    void ask(input.value);
  }
}
</script>

<template>
  <Teleport to="body">
    <section v-if="open" class="mc-panel" aria-label="比赛分析助手">
      <header class="mc-head">
        <div class="mc-head-id">
          <span class="mc-avatar bot" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="16" height="16">
              <rect x="7" y="9" width="18" height="14" fill="none" stroke="currentColor" stroke-width="2" />
              <rect x="12" y="4" width="8" height="5" fill="currentColor" />
              <circle cx="13" cy="16" r="1.6" fill="currentColor" />
              <circle cx="19" cy="16" r="1.6" fill="currentColor" />
              <path d="M13 21h6" stroke="currentColor" stroke-width="2" />
            </svg>
          </span>
          <div>
            <div class="mc-title">比赛分析助手</div>
            <div class="mc-kicker">Grok 4.6 · 查库回答</div>
          </div>
        </div>
        <div class="mc-head-actions">
          <button type="button" class="mc-icon-btn" @click="reset">新对话</button>
          <button type="button" class="mc-icon-btn" aria-label="关闭" @click="open = false">×</button>
        </div>
      </header>

      <div ref="scroller" class="mc-body">
        <div v-if="!messages.length" class="mc-welcome">
          <span class="mc-welcome-icon" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="22" height="22">
              <rect x="7" y="9" width="18" height="14" fill="none" stroke="currentColor" stroke-width="2" />
              <rect x="12" y="4" width="8" height="5" fill="currentColor" />
              <circle cx="13" cy="16" r="1.6" fill="currentColor" />
              <circle cx="19" cy="16" r="1.6" fill="currentColor" />
              <path d="M13 21h6" stroke="currentColor" stroke-width="2" />
            </svg>
          </span>
          <div class="mc-welcome-main">
            <h3 class="mc-welcome-title">你好，我是比赛分析助手</h3>
            <p class="mc-welcome-desc">
              问积分榜、选手近况和对位交锋。我会先查库里的真实赛果，再给你结论。
            </p>
          </div>
        </div>

        <div v-if="!messages.length" class="mc-prompts">
          <div class="mc-prompts-title">你可以这样问</div>
          <button
            v-for="item in PROMPTS"
            :key="item.key"
            type="button"
            class="mc-prompt"
            @click="ask(item.ask)"
          >
            <span class="mc-prompt-label">{{ item.label }}</span>
            <span class="mc-prompt-desc">{{ item.description }}</span>
          </button>
        </div>

        <div v-for="(msg, i) in messages" :key="i" class="mc-bubble" :class="msg.role">
          <span class="mc-avatar" :class="msg.role === 'user' ? 'user' : 'bot'" aria-hidden="true">
            <template v-if="msg.role === 'user'">我</template>
            <svg v-else viewBox="0 0 32 32" width="14" height="14">
              <rect x="7" y="9" width="18" height="14" fill="none" stroke="currentColor" stroke-width="2" />
              <rect x="12" y="4" width="8" height="5" fill="currentColor" />
              <circle cx="13" cy="16" r="1.6" fill="currentColor" />
              <circle cx="19" cy="16" r="1.6" fill="currentColor" />
              <path d="M13 21h6" stroke="currentColor" stroke-width="2" />
            </svg>
          </span>
          <div class="mc-col">
            <div class="mc-role">{{ msg.role === "user" ? "你" : "助手" }}</div>
            <div
              v-if="msg.role === 'assistant' && !msg.error"
              class="mc-content html"
              v-html="formatChatHtml(msg.text)"
            />
            <div v-else class="mc-content" :class="{ error: msg.error }">{{ msg.text }}</div>
            <div v-if="msg.tools?.length" class="mc-meta">
              已查阅 {{ msg.tools.map(toolLabel).join(" · ") }}
            </div>
          </div>
        </div>

        <div v-if="loading" class="mc-bubble assistant">
          <span class="mc-avatar bot" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="14" height="14">
              <rect x="7" y="9" width="18" height="14" fill="none" stroke="currentColor" stroke-width="2" />
              <rect x="12" y="4" width="8" height="5" fill="currentColor" />
              <circle cx="13" cy="16" r="1.6" fill="currentColor" />
              <circle cx="19" cy="16" r="1.6" fill="currentColor" />
              <path d="M13 21h6" stroke="currentColor" stroke-width="2" />
            </svg>
          </span>
          <div class="mc-col">
            <div class="mc-role">助手</div>
            <div class="mc-content loading">
              <span class="mc-dots" aria-hidden="true"><i /><i /><i /></span>
              正在查阅比赛数据
            </div>
          </div>
        </div>
      </div>

      <form class="mc-sender" @submit="onSubmit">
        <textarea
          v-model="input"
          rows="2"
          placeholder="问一场球、一个排名、一次对位"
          :disabled="loading"
          @keydown="onKeydown"
        />
        <div class="mc-sender-bar">
          <span class="mc-hint">Enter 发送 · Shift+Enter 换行</span>
          <button type="submit" class="mc-send" :disabled="loading || !input.trim()">发送</button>
        </div>
      </form>
    </section>

    <button
      type="button"
      class="mc-fab"
      :class="{ open }"
      :aria-expanded="open"
      :aria-label="open ? '关闭助手' : '打开比赛分析助手'"
      @click="toggle"
    >
      <svg v-if="!open" viewBox="0 0 32 32" width="22" height="22" aria-hidden="true">
        <rect x="7" y="9" width="18" height="14" fill="none" stroke="currentColor" stroke-width="2" />
        <rect x="12" y="4" width="8" height="5" fill="currentColor" />
        <circle cx="13" cy="16" r="1.6" fill="currentColor" />
        <circle cx="19" cy="16" r="1.6" fill="currentColor" />
        <path d="M13 21h6" stroke="currentColor" stroke-width="2" />
      </svg>
      <span v-else aria-hidden="true">×</span>
    </button>
  </Teleport>
</template>

<style scoped>
.mc-panel {
  position: fixed;
  right: 20px;
  bottom: 88px;
  z-index: 80;
  box-sizing: border-box;
  width: 400px;
  height: 560px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 120px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border: 1px solid var(--line);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55);
}

.mc-fab {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 81;
  appearance: none;
  width: 56px;
  height: 56px;
  border: 1px solid var(--red);
  background: var(--red);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  line-height: 1;
}

.mc-fab.open {
  background: var(--cell);
  border-color: var(--line);
  color: var(--text);
}

.mc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex: none;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, #1a1a1d 0%, var(--cell) 100%);
}

.mc-head-id {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.mc-head-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mc-kicker {
  color: var(--muted);
  font-size: 11px;
}

.mc-title {
  font-family: "Barlow Condensed", sans-serif;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.1;
}

.mc-icon-btn {
  appearance: none;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--muted);
  height: 28px;
  min-width: 28px;
  padding: 0 10px;
  cursor: pointer;
  font-size: 12px;
}

.mc-icon-btn:hover {
  color: var(--text);
  border-color: var(--red);
}

.mc-avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: "Barlow Condensed", sans-serif;
  font-size: 13px;
  font-weight: 700;
}

.mc-avatar.bot {
  background: var(--red);
  color: #fff;
}

.mc-avatar.user {
  background: var(--cell);
  color: var(--text);
  border: 1px solid var(--line);
}

.mc-body {
  flex: 1 1 0%;
  min-height: 0;
  min-width: 0;
  overflow: auto;
  padding: 16px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-sizing: border-box;
}

.mc-welcome {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 12px;
  padding: 14px;
  background: linear-gradient(120deg, #2a1212 0%, var(--cell) 58%);
  border: 1px solid #3a1c1c;
}

.mc-welcome-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--red);
  color: #fff;
}

.mc-welcome-title {
  margin: 0 0 6px;
  font-family: "Barlow Condensed", sans-serif;
  font-size: 22px;
  font-weight: 800;
}

.mc-welcome-desc {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.55;
}

.mc-prompts-title {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 12px;
}

.mc-prompt {
  appearance: none;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  margin-bottom: 8px;
  text-align: left;
  padding: 10px 12px;
  background: var(--cell);
  border: 1px solid var(--line);
  color: var(--text);
  cursor: pointer;
}

.mc-prompt:hover {
  border-color: var(--red);
}

.mc-prompt-label {
  font-family: "Barlow Condensed", sans-serif;
  font-size: 16px;
  font-weight: 700;
}

.mc-prompt-desc {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
}

.mc-bubble {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  column-gap: 8px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.mc-bubble.user {
  grid-template-columns: minmax(0, 1fr) 32px;
}

.mc-bubble.user .mc-avatar {
  grid-column: 2;
}

.mc-bubble.user .mc-col {
  grid-column: 1;
  text-align: right;
}

.mc-col {
  min-width: 0;
  max-width: 100%;
}

.mc-role {
  color: var(--muted);
  font-size: 11px;
  margin-bottom: 4px;
}

.mc-content {
  box-sizing: border-box;
  max-width: 100%;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.55;
  overflow-wrap: anywhere;
  word-break: break-word;
  background: var(--cell);
  border: 1px solid var(--line);
}

.mc-content.html {
  white-space: normal;
}

.mc-content.html strong {
  font-weight: 700;
  color: #fff;
}

.mc-bubble.user .mc-content {
  display: inline-block;
  background: var(--red);
  border-color: var(--red);
  color: #fff;
  text-align: left;
}

.mc-content.error {
  border-color: #5a2020;
  color: #ffb4b4;
}

.mc-content.loading {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
}

.mc-meta {
  margin-top: 6px;
  color: var(--muted);
  font-size: 11px;
}

.mc-dots {
  display: inline-flex;
  gap: 3px;
}

.mc-dots i {
  width: 5px;
  height: 5px;
  background: var(--muted);
  display: block;
  animation: mc-dot 1s ease-in-out infinite;
}

.mc-dots i:nth-child(2) {
  animation-delay: 0.15s;
}

.mc-dots i:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes mc-dot {
  0%,
  80%,
  100% {
    opacity: 0.25;
  }
  40% {
    opacity: 1;
  }
}

.mc-sender {
  flex: none;
  margin: 0 12px 12px;
  padding: 8px 8px 8px 10px;
  background: var(--cell);
  border: 1px solid var(--line);
  box-sizing: border-box;
}

.mc-sender textarea {
  display: block;
  width: 100%;
  max-width: 100%;
  resize: none;
  background: transparent;
  color: var(--text);
  border: 0;
  padding: 4px 2px 8px;
  font-family: "IBM Plex Sans", sans-serif;
  font-size: 13px;
  line-height: 1.5;
  box-sizing: border-box;
}

.mc-sender textarea:focus {
  outline: 0;
}

.mc-sender-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.mc-hint {
  color: var(--muted);
  font-size: 11px;
}

.mc-send {
  appearance: none;
  border: 0;
  background: var(--red);
  color: #fff;
  height: 28px;
  padding: 0 12px;
  cursor: pointer;
  font-family: "Barlow Condensed", sans-serif;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.mc-send:disabled {
  opacity: 0.45;
  cursor: default;
}

.mc-sender:focus-within {
  border-color: var(--red);
}
</style>
