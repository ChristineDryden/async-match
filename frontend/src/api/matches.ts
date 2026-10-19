import http from "./http";
import type { MatchesResponse, SyncResponse } from "../types/match";

export function fetchMatches() {
  return http.get<MatchesResponse>("/api/matches").then((res) => res.data);
}

export function syncMatches() {
  return http.post<SyncResponse>("/api/sync").then((res) => res.data);
}
