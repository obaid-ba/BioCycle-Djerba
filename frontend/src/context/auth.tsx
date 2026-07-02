import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  clearTokens,
  configureAuthHandlers,
  getAccessToken,
} from "@/services/api";
import * as authService from "@/services/auth";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  /** True while the initial session is being restored from a stored token. */
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // A ref so the api-layer handlers always see the latest logout without being
  // reconfigured on every render.
  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);
  const logoutRef = useRef(logout);
  logoutRef.current = logout;

  // Wire the api layer's refresh + session-expiry hooks exactly once.
  useEffect(() => {
    configureAuthHandlers({
      refresh: authService.refresh,
      onSessionExpired: () => logoutRef.current(),
    });
  }, []);

  // Restore the session on mount: if a token exists, resolve the user via /me.
  useEffect(() => {
    let active = true;

    async function restore() {
      if (!getAccessToken()) {
        if (active) setIsLoading(false);
        return;
      }
      try {
        const me = await authService.getMe();
        if (active) setUser(me);
      } catch {
        // Interceptor already attempted refresh; a failure here means the
        // session is unrecoverable.
        clearTokens();
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void restore();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await authService.login(email, password);
    const me = await authService.getMe();
    setUser(me);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      login,
      logout,
    }),
    [user, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
