import axios from "axios";

export const TOKEN_KEY = "nursery_token";

export const api = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api` });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (e) => {
    const path = window.location.pathname;
    if (e.response?.status === 401 && !e.config.url.startsWith("/auth/") && path !== "/login") {
      localStorage.removeItem(TOKEN_KEY);
      window.location.href = "/login";
    }
    return Promise.reject(e);
  }
);

export function errorMessage(e) {
  const d = e?.response?.data?.detail;
  if (d == null) return "Si è verificato un errore. Riprova.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (typeof x?.msg === "string" ? x.msg : JSON.stringify(x))).join(" ");
  if (typeof d.message === "string") return d.message;
  return String(d);
}
