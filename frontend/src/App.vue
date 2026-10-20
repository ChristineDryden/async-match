<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import ChatAssistant from "./components/ChatAssistant.vue";

const route = useRoute();
const showAssistant = computed(() => route.name !== "login");
</script>

<template>
  <router-view />
  <ChatAssistant v-if="showAssistant" />
</template>
