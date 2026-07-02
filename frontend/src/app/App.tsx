import { Loader2 } from "lucide-react";
import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";

// Lazy-loaded routes — each page is split into its own chunk so the initial
// bundle stays small (charts/map libs only load when their page is visited).
const Login = lazy(() => import("@/pages/Login").then((m) => ({ default: m.Login })));
const Dashboard = lazy(() =>
  import("@/pages/Dashboard").then((m) => ({ default: m.Dashboard })),
);
const Hotels = lazy(() => import("@/pages/Hotels").then((m) => ({ default: m.Hotels })));
const Bins = lazy(() => import("@/pages/Bins").then((m) => ({ default: m.Bins })));
const Collections = lazy(() =>
  import("@/pages/Collections").then((m) => ({ default: m.Collections })),
);
const Alerts = lazy(() => import("@/pages/Alerts").then((m) => ({ default: m.Alerts })));
const Users = lazy(() => import("@/pages/Users").then((m) => ({ default: m.Users })));

function RouteFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Loader2 className="size-6 animate-spin text-muted-foreground" />
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/hotels" element={<Hotels />} />
          <Route path="/bins" element={<Bins />} />
          <Route path="/collections" element={<Collections />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route
            path="/users"
            element={
              <ProtectedRoute roles={["admin"]}>
                <Users />
              </ProtectedRoute>
            }
          />
        </Route>
      </Routes>
    </Suspense>
  );
}
