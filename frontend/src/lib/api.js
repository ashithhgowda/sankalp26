import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true });

let accessToken = null;
let csrfToken = null;

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  if (["post", "put", "patch", "delete"].includes(config.method)) {
    const cookieToken = document.cookie.split("; ").find((row) => row.startsWith("csrf_token="))?.split("=")[1];
    const token = csrfToken || (cookieToken ? decodeURIComponent(cookieToken) : null);
    if (token) {
      config.headers = config.headers || {};
      config.headers["X-CSRF-Token"] = token;
    }
  }
  return config;
});

export function clearAccessToken() {
  accessToken = null;
  csrfToken = null;
}

let refreshing = null;
api.interceptors.response.use((response) => {
  if (typeof response.data?.token === "string") accessToken = response.data.token;
  if (typeof response.data?.csrf_token === "string") csrfToken = response.data.csrf_token;
  else if (typeof response.headers?.["x-csrf-token"] === "string") csrfToken = response.headers["x-csrf-token"];
  return response;
}, async (error) => {
  const original = error.config;
  const responseCsrf = error.response?.headers?.["x-csrf-token"];
  if (typeof responseCsrf === "string") csrfToken = responseCsrf;
  if (error.response?.status === 403 && error.response?.data?.detail === "CSRF validation failed" &&
      typeof responseCsrf === "string" && original && !original._csrfRetried) {
    original._csrfRetried = true;
    return api(original);
  }
  const neverRefresh = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/activate", "/auth/forgot-password", "/auth/reset-password"];
  if (error.response?.status === 401 && !original?._retried && !neverRefresh.some((path) => original?.url?.includes(path))) {
    original._retried = true;
    refreshing ||= api.post("/auth/refresh").finally(() => { refreshing = null; });
    await refreshing;
    return api(original);
  }
  throw error;
});

export function formatErr(e) {
  const detail = e?.response?.data?.detail;
  if (detail == null) return e?.message || "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d && typeof d.msg === "string" ? d.msg : JSON.stringify(d))).join(" ");
  if (typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export async function downloadFile(fileId, filename) {
  const r = await api.get(`/files/${fileId}`, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function youtubeEmbed(url = "") {
  const m = url.match(/(?:youtu\.be\/|v=|embed\/|shorts\/)([\w-]{11})/);
  return m ? `https://www.youtube.com/embed/${m[1]}` : null;
}
