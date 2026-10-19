import { createRouter, createWebHistory } from "vue-router";
import StandingsView from "../views/StandingsView.vue";
import PlayerView from "../views/PlayerView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "standings", component: StandingsView },
    { path: "/player", name: "player", component: PlayerView },
    {
      path: "/player.html",
      redirect: (to) => ({ path: "/player", query: to.query }),
    },
  ],
});

export default router;
