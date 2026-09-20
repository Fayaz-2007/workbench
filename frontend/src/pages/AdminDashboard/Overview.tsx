import { AlertCircle, Activity, Cpu, Server, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { AdminHeader } from "../../components/admin/AdminHeader";
import { StatCard } from "../../components/admin/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";
import { EmptyState } from "../../components/common/EmptyState";
import { formatTimestamp } from "../../lib/utils";
import { getAdminOverview } from "../../services/api/client";
import type { AdminOverview as AdminOverviewData } from "../../types";
import { useAdminOutletContext } from "./AdminLayout";

export function Overview() {
  const { onOpenMobileMenu } = useAdminOutletContext();
  const [data, setData] = useState<AdminOverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminOverview()
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load the admin overview.");
      });
  }, []);

  return (
    <>
      <AdminHeader
        title="Overview"
        description="System status at a glance"
        onOpenMobileMenu={onOpenMobileMenu}
      />
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {error && (
          <p className="mb-4 flex items-center gap-1.5 text-sm text-danger-500">
            <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
            {error}
          </p>
        )}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={Server}
            label="System Status"
            value={data ? capitalize(data.systemStatus) : "…"}
            hint="Local server not yet deployed"
          />
          <StatCard
            icon={Activity}
            label="External Connections"
            value={data ? formatConnectionState(data.externalConnections) : "…"}
            hint="No outbound network calls configured"
          />
          <StatCard
            icon={Users}
            label="Active Sessions"
            value={data?.activeSessions?.toString() ?? "—"}
            hint="This device only"
          />
          <StatCard
            icon={Cpu}
            label="Models Online"
            value={data ? `${data.modelsOnline ?? 0} / ${data.modelsTotal ?? 0}` : "…"}
            hint="See Models for details"
          />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <Badge tone="neutral">This session only</Badge>
            </CardHeader>
            <CardContent className="p-0">
              {data && data.recentActivity.length === 0 ? (
                <EmptyState icon={Activity} title="No activity yet" description="Actions taken in this session will appear here." />
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="text-neutral-400">
                    <tr>
                      <th className="px-4 py-2 font-medium">Action</th>
                      <th className="px-4 py-2 font-medium">Resource</th>
                      <th className="px-4 py-2 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {data?.recentActivity.map((entry) => (
                      <tr key={entry.id}>
                        <td className="whitespace-nowrap px-4 py-2.5 text-neutral-800">{entry.action}</td>
                        <td className="whitespace-nowrap px-4 py-2.5 text-neutral-500">{entry.resource}</td>
                        <td className="whitespace-nowrap px-4 py-2.5 text-neutral-400">
                          {formatTimestamp(entry.timestamp)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Network Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-neutral-500">
              <p>Live local vs. external connection monitoring is available on the Network page.</p>
              <p className="pt-1 text-xs text-neutral-400">See Network for a live breakdown, and Security for the full sovereignty status.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatConnectionState(state: AdminOverviewData["externalConnections"]): string {
  if (state === "not_connected") return "Not connected";
  if (state === "connected") return "Connected";
  return "Unknown";
}
