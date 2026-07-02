import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

import { env } from "@/lib/env";

/**
 * Shared axios instance. The request interceptor attaches the access token; the
 * response interceptor transparently refreshes it on a 401 and retries once.
 */
export const api = axios.create({
  baseURL: env.apiUrl,
  headers: { "Content-Type": "application/json" },
});

const ACCESS_TOKEN_KEY = "biocycle.access_token";
const REFRESH_TOKEN_KEY = "biocycle.refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string | null, refresh?: string | null): void {
  if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access);
  else localStorage.removeItem(ACCESS_TOKEN_KEY);

  if (refresh !== undefined) {
    if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
    else localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * When the access token is rejected once, invoke this to obtain a fresh one.
 * Wired by the auth layer so the interceptor stays free of feature imports and
 * we avoid a circular dependency between `api` and the auth service.
 */
type Refresher = () => Promise<string | null>;
let refresher: Refresher | null = null;

/** Called if refresh fails — the auth layer clears state and redirects to login. */
type SessionExpiredHandler = () => void;
let onSessionExpired: SessionExpiredHandler | null = null;

export function configureAuthHandlers(handlers: {
  refresh: Refresher;
  onSessionExpired: SessionExpiredHandler;
}): void {
  refresher = handlers.refresh;
  onSessionExpired = handlers.onSessionExpired;
}

// Single-flight: concurrent 401s share one refresh round-trip.
let refreshInFlight: Promise<string | null> | null = null;

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    const status = error.response?.status;

    if (
      status !== 401 ||
      !original ||
      original._retried ||
      !refresher ||
      !getRefreshToken()
    ) {
      return Promise.reject(error);
    }

    original._retried = true;

    try {
      refreshInFlight = refreshInFlight ?? refresher();
      const newToken = await refreshInFlight;
      if (!newToken) throw new Error("refresh returned no token");

      original.headers.Authorization = `Bearer ${newToken}`;
      return api(original as AxiosRequestConfig);
    } catch (refreshError) {
      onSessionExpired?.();
      return Promise.reject(refreshError);
    } finally {
      refreshInFlight = null;
    }
  },
);
