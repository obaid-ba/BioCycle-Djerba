import { Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";
import { Alerts } from "@/pages/Alerts";
import { Bins } from "@/pages/Bins";
import { Collections } from "@/pages/Collections";
import { Dashboard } from "@/pages/Dashboard";
import { Hotels } from "@/pages/Hotels";
import { Login } from "@/pages/Login";
import { Users } from "@/pages/Users";

export default function App() {
  return (
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
  );
}
