/** Typed, defaulted access to Vite environment variables. */
export const env = {
  apiUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
  wsUrl: import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/api/ws",
} as const;
