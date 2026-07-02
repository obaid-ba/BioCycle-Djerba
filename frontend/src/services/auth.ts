import axios from "axios";

import { env } from "@/lib/env";
import { api, getRefreshToken, setTokens } from "@/services/api";
import type { TokenResponse, User } from "@/types";

/** POST /auth/login — exchange credentials for a token pair. */
export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", {
    email,
    password,
  });
  setTokens(data.access_token, data.refresh_token);
  return data;
}

/**
 * POST /auth/refresh — trade the stored refresh token for a new pair.
 *
 * Uses a bare axios call (not the shared `api`) so a 401 here does not trigger
 * the response interceptor and recurse. Returns the new access token, or null
 * when there is nothing to refresh with.
 */
export async function refresh(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  const { data } = await axios.post<TokenResponse>(
    `${env.apiUrl}/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { "Content-Type": "application/json" } },
  );
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

/** GET /auth/me — hydrate the current user from a valid access token. */
export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}
