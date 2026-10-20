<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { login } from "../api/auth";
import { markLoggedIn } from "../router";

const route = useRoute();
const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");
const submitting = ref(false);

function safeRedirect(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
  }
  if (value.startsWith("/login")) return "/";
  return value;
}

async function submit() {
  error.value = "";
  submitting.value = true;
  try {
    const data = await login(username.value.trim(), password.value);
    markLoggedIn(data.user);
    await router.replace(safeRedirect(route.query.redirect));
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    error.value = status === 401 ? "账号或密码不正确" : "登录失败，请稍后再试";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main class="gate">
    <section class="scoreboard">
      <p class="league">Valhalla League</p>
      <h1>进场前先登录</h1>
      <p class="lead">积分榜、选手页和同步都在登录之后。</p>
      <form @submit.prevent="submit">
        <label>
          账号
          <input v-model="username" name="username" autocomplete="username" required />
        </label>
        <label>
          密码
          <input
            v-model="password"
            name="password"
            type="password"
            autocomplete="current-password"
            required
          />
        </label>
        <p v-if="error" class="gate-error" role="alert">{{ error }}</p>
        <button class="action primary" type="submit" :disabled="submitting">
          {{ submitting ? "正在核对" : "进入积分榜" }}
        </button>
      </form>
    </section>
  </main>
</template>
