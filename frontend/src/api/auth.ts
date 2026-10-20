import http from "./http";

export interface AuthUser {
  user: string;
}

export function fetchMe() {
  return http.get<AuthUser>("/api/auth/me").then((res) => res.data);
}

export function login(username: string, password: string) {
  return http
    .post<AuthUser>("/api/auth/login", { username, password })
    .then((res) => res.data);
}

export function logout() {
  return http.post("/api/auth/logout").then((res) => res.data);
}
