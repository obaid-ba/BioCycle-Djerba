import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/context/auth";
import { useToast } from "@/context/toast";
import { env } from "@/lib/env";
import { getAccessToken } from "@/services/api";
import type { RealtimeEvent } from "@/types";

type ConnectionState = "connecting" | "open" | "closed";

interface RealtimeContextValue {
  status: ConnectionState;
}

const RealtimeContext = createContext<RealtimeContextValue>({ status: "closed" });

/**
 * Owns a single dashboard WebSocket for the authenticated session. On each event
 * it invalidates the relevant React Query caches (so lists/dashboard refetch)
 * and toasts newly-raised alerts. Reconnects with capped backoff; tears down on
 * logout.
 */
export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [status, setStatus] = useState<ConnectionState>("closed");

  // Keep latest deps in refs so the socket effect doesn't reconnect on every
  // render — it should only re-run when auth changes.
  const qcRef = useRef(queryClient);
  qcRef.current = queryClient;
  const toastRef = useRef(toast);
  toastRef.current = toast;

  useEffect(() => {
    if (!isAuthenticated) {
      setStatus("closed");
      return;
    }

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;
    let closedByUs = false;

    const connect = () => {
      const token = getAccessToken();
      if (!token) return;

      setStatus("connecting");
      ws = new WebSocket(`${env.wsUrl}?token=${encodeURIComponent(token)}`);

      ws.onopen = () => {
        attempt = 0;
        setStatus("open");
      };

      ws.onmessage = (e) => {
        let event: RealtimeEvent;
        try {
          event = JSON.parse(e.data as string);
        } catch {
          return;
        }
        handleEvent(event);
      };

      ws.onclose = () => {
        setStatus("closed");
        if (closedByUs) return;
        // Exponential backoff capped at 30s.
        const delay = Math.min(1000 * 2 ** attempt, 30_000);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };

      ws.onerror = () => ws?.close();
    };

    const handleEvent = (event: RealtimeEvent) => {
      const qc = qcRef.current;
      switch (event.type) {
        case "notification":
          // Targeted to this user by the backend; refresh the bell + toast it.
          qc.invalidateQueries({ queryKey: ["notifications"] });
          toastRef.current.toast(event.data.title, "info");
          break;
        case "connection.ack":
          break;
      }
    };

    connect();

    return () => {
      closedByUs = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [isAuthenticated]);

  return (
    <RealtimeContext.Provider value={{ status }}>
      {children}
    </RealtimeContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useRealtimeStatus(): ConnectionState {
  return useContext(RealtimeContext).status;
}
