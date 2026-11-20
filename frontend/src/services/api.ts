import axios, { type AxiosProgressEvent } from "axios";
import type { Analysis, Dashboard, Metrics, ModelInfo, User } from "../types";

/** All requests go to /api (proxied to FastAPI by Vite in development and nginx in Docker). */
export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
export const http = axios.create({ baseURL: API_BASE, timeout: 120_000, withCredentials: true });

// Called when the session has expired, so the app can return to the login page.
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn; }
http.interceptors.response.use((r) => r, (err) => {
  const url: string = err?.config?.url ?? "";
  if (err?.response?.status === 401 && !url.startsWith("/auth/")) onUnauthorized?.();
  return Promise.reject(err);
});

// Requests started inside `withSignal` inherit its AbortSignal so the useApi
// hook can cancel them when a page changes.
let ambientSignal: AbortSignal | null = null;
export function withSignal<T>(signal: AbortSignal, start: () => Promise<T>): Promise<T> {
  ambientSignal = signal;
  try {
    const p = start();
    return new Promise<T>((resolve, reject) => {
      if (signal.aborted) { reject(new axios.CanceledError()); return; }
      signal.addEventListener("abort", () => reject(new axios.CanceledError()), { once: true });
      p.then(resolve, reject);
    });
  } finally {
    ambientSignal = null;
  }
}
http.interceptors.request.use((config) => {
  if (!config.signal && ambientSignal) config.signal = ambientSignal;
  return config;
}, undefined, { synchronous: true });

export const isCancel = (e: unknown) => axios.isCancel(e);

export function errorMessage(err: unknown, fallback = "Something went wrong. Please try again."): string {
  if (axios.isAxiosError(err)) {
    if (!err.response) return "Cannot reach the server. Make sure the backend is running.";
    const d = (err.response.data as { detail?: unknown })?.detail;
    if (typeof d === "string") return d;
    if (err.response.status === 413) return "The file is too large.";
  }
  return fallback;
}

export const assetUrl = (path: string) => `${API_BASE}${path}`;

export const authApi = {
  me: () => http.get<User>("/auth/me").then((r) => r.data),
  login: (email: string, password: string, remember = true) =>
    http.post<User>("/auth/login", { email, password, remember }).then((r) => r.data),
  register: (name: string, email: string, password: string) =>
    http.post<User>("/auth/register", { name, email, password }).then((r) => r.data),
  logout: () => http.post("/auth/logout"),
};

export const api = {
  dashboard: () => http.get<Dashboard>("/dashboard").then((r) => r.data),
  modelInfo: () => http.get<ModelInfo>("/model-info").then((r) => r.data),
  metrics: () => http.get<Metrics>("/metrics").then((r) => r.data),
  history: () => http.get<{ items: Analysis[]; total: number }>("/analysis/history", { params: { limit: 200 } }).then((r) => r.data),
  analysis: (id: string) => http.get<Analysis>(`/analysis/${id}`).then((r) => r.data),
  remove: (id: string) => http.delete(`/analysis/${id}`),
  gradcam: (id: string) => http.post<Analysis>(`/analysis/${id}/gradcam`).then((r) => r.data),
  triage: (file: File, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append("file", file);
    return http.post<Analysis>("/triage", fd, {
      onUploadProgress: (e: AxiosProgressEvent) => e.total && onProgress?.(Math.round((e.loaded / e.total) * 100)),
    }).then((r) => r.data);
  },
};
