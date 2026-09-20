import type { AuditLogEntry } from "../../types";

/** Audit logging is a later segment's real feature — the Audit Logs page
 * stays on this mock data until then (see backend/README.md).
 */
export const MOCK_AUDIT_LOGS: AuditLogEntry[] = [
  {
    id: "log_1",
    timestamp: new Date(Date.now() - 1000 * 60 * 8).toISOString(),
    user: "dev@local",
    action: "Signed in",
    resource: "Admin Dashboard",
    status: "success",
  },
  {
    id: "log_2",
    timestamp: new Date(Date.now() - 1000 * 60 * 40).toISOString(),
    user: "dev@local",
    action: "Started conversation",
    resource: "Code Agent",
    status: "success",
  },
  {
    id: "log_3",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    user: "dev@local",
    action: "Uploaded attachment",
    resource: "turbine-schematic.png",
    status: "success",
  },
];
