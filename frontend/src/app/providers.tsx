import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "@/context/auth";
import { RealtimeProvider } from "@/context/realtime";
import { ThemeProvider } from "@/context/theme";
import { ToastProvider } from "@/context/toast";
import { queryClient } from "@/services/queryClient";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <BrowserRouter>
            <AuthProvider>
              <RealtimeProvider>{children}</RealtimeProvider>
            </AuthProvider>
          </BrowserRouter>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
