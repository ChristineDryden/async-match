import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? "",
  timeout: 180_000,
  withCredentials: true,
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = String(error?.config?.url ?? "");
    if (status === 401 && !url.includes("/api/auth/")) {
      window.dispatchEvent(new CustomEvent("auth:required"));
    }
    return Promise.reject(error);
  },
);

export default http;
