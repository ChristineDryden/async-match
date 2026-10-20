import { createRouter, createWebHistory } from "vue-router";
import { fetchMe } from "../api/auth";
import StandingsView from "../views/StandingsView.vue";
import PlayerView from "../views/PlayerView.vue";
import LoginView from "../views/LoginView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/", name: "standings", component: StandingsView },
    { path: "/player", name: "player", component: PlayerView },
    {
      path: "/player.html",
      redirect: (to) => ({ path: "/player", query: to.query }),
    },
  ],
});

let knownUser: string | null | undefined;

export function markLoggedIn(user: string) {
  knownUser = user;
}

export function markLoggedOut() {
  knownUser = null;
}

async function resolveUser(): Promise<string | null> {
  if (knownUser !== undefined) return knownUser;
  try {
    const data = await fetchMe();
    knownUser = data.user;
  } catch {
    knownUser = null;
  }
  return knownUser;
}

router.beforeEach(async (to) => {
  const user = await resolveUser();
  if (to.meta.public) {
    if (user && to.name === "login") return { path: "/" };
    return true;
  }
  if (!user) {
    return {
      name: "login",
      query: to.fullPath && to.fullPath !== "/" ? { redirect: to.fullPath } : {},
    };
  }
  return true;
});

if (typeof window !== "undefined") {
  window.addEventListener("auth:required", () => {
    if (knownUser === null && router.currentRoute.value.name === "login") return;
    markLoggedOut();
    const current = router.currentRoute.value.fullPath;
    if (router.currentRoute.value.name === "login") return;
    router.replace({
      name: "login",
      query: current && current !== "/" ? { redirect: current } : {},
    });
  });
}

export default router;
