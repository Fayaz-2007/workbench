import { useEffect, useState } from "react";
import { AdminHeader } from "../../components/admin/AdminHeader";
import { Card } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";
import { formatTimestamp } from "../../lib/utils";
import { getAuditLogs } from "../../services/api/client";
import type { AuditLogEntry } from "../../types";
import type { BadgeTone } from "../../components/common/Badge";
import { useAdminOutletContext } from "./AdminLayout";

const STATUS_TONE: Record<AuditLogEntry["status"], BadgeTone> = {
  success: "success",
  failure: "danger",
  pending: "warning",
};

export function AuditLogs() {
  const { onOpenMobileMenu } = useAdminOutletContext();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);

  useEffect(() => {
    getAuditLogs().then(setLogs);
  }, []);

  return (
    <>
      <AdminHeader title="Audit Logs" description="Every recorded action in this workbench" onOpenMobileMenu={onOpenMobileMenu} />
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <Badge tone="neutral" className="mb-4">
          Development data
        </Badge>

        <Card className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-neutral-150 text-neutral-400">
              <tr>
                <th className="px-4 py-2.5 font-medium">Timestamp</th>
                <th className="px-4 py-2.5 font-medium">User</th>
                <th className="px-4 py-2.5 font-medium">Action</th>
                <th className="px-4 py-2.5 font-medium">Resource</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {logs.map((log) => (
                <tr key={log.id}>
                  <td className="whitespace-nowrap px-4 py-3 text-neutral-500">{formatTimestamp(log.timestamp)}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-neutral-800">{log.user}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-neutral-700">{log.action}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-neutral-500">{log.resource}</td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <Badge tone={STATUS_TONE[log.status]}>{log.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </>
  );
}
