import { Route, Routes } from "react-router-dom";
import { UserWorkbench } from "../pages/UserWorkbench";
import { WorkbenchProvider } from "../context/WorkbenchContext";
import { AdminLayout } from "../pages/AdminDashboard/AdminLayout";
import { Overview } from "../pages/AdminDashboard/Overview";
import { Models } from "../pages/AdminDashboard/Models";
import { Users } from "../pages/AdminDashboard/Users";
import { System } from "../pages/AdminDashboard/System";
import { Network } from "../pages/AdminDashboard/Network";
import { Security } from "../pages/AdminDashboard/Security";
import { AuditLogs } from "../pages/AdminDashboard/AuditLogs";
import { Settings } from "../pages/AdminDashboard/Settings";

export function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <WorkbenchProvider>
            <UserWorkbench />
          </WorkbenchProvider>
        }
      />
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<Overview />} />
        <Route path="models" element={<Models />} />
        <Route path="users" element={<Users />} />
        <Route path="system" element={<System />} />
        <Route path="network" element={<Network />} />
        <Route path="security" element={<Security />} />
        <Route path="audit-logs" element={<AuditLogs />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
