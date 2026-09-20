import { useEffect, useState } from "react";
import { AdminHeader } from "../../components/admin/AdminHeader";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";
import { getSystemStatus } from "../../services/api/client";
import type { SystemStatus } from "../../types";
import { useAdminOutletContext } from "./AdminLayout";

const REFRESH_MS = 5000;

function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d ${hours % 24}h`;
  return `${hours}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export function System() {
  const { onOpenMobileMenu } = useAdminOutletContext();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      getSystemStatus()
        .then((result) => {
          if (!cancelled) {
            setStatus(result);
            setError(null);
          }
        })
        .catch((err: unknown) => {
          if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load system status.");
        });
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const metrics: { label: string; value: string | null }[] = status
    ? [
        { label: "CPU", value: `${status.cpuPercent.toFixed(0)}%` },
        { label: "RAM", value: `${status.ramPercent.toFixed(0)}%` },
        { label: "Disk", value: `${status.diskPercent.toFixed(0)}%` },
        { label: "Processes", value: String(status.processCount) },
      ]
    : [
        { label: "CPU", value: null },
        { label: "RAM", value: null },
        { label: "Disk", value: null },
        { label: "Processes", value: null },
      ];

  return (
    <>
      <AdminHeader title="System" description="Resource usage on the host machine — LOCAL DATA" onOpenMobileMenu={onOpenMobileMenu} />
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {error && <p className="mb-4 text-sm text-danger-500">{error}</p>}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <Card key={metric.label} className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">{metric.label}</p>
              <p className="mt-2 text-2xl font-semibold text-neutral-900">
                {metric.value ?? <span className="text-base font-medium text-neutral-300">Loading…</span>}
              </p>
            </Card>
          ))}
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Host</CardTitle>
              <Badge tone="success">LOCAL DATA</Badge>
            </CardHeader>
            <CardContent className="space-y-1.5 text-sm text-neutral-600">
              {status ? (
                <>
                  <p>Hostname: <span className="font-medium text-neutral-900">{status.hostname}</span></p>
                  <p>OS: <span className="font-medium text-neutral-900">{status.operatingSystem}</span></p>
                  <p>Local IP: <span className="font-medium text-neutral-900">{status.localIp ?? "unavailable"}</span></p>
                  <p>Uptime: <span className="font-medium text-neutral-900">{formatUptime(status.uptimeSeconds)}</span></p>
                </>
              ) : (
                <p className="text-neutral-400">Loading…</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Storage & Memory</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5 text-sm text-neutral-600">
              {status ? (
                <>
                  <p>RAM: <span className="font-medium text-neutral-900">{status.ramUsedGb.toFixed(1)} / {status.ramTotalGb.toFixed(1)} GB</span></p>
                  <p>Disk: <span className="font-medium text-neutral-900">{status.diskUsedGb.toFixed(1)} / {status.diskTotalGb.toFixed(1)} GB</span></p>
                </>
              ) : (
                <p className="text-neutral-400">Loading…</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
