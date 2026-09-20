import { useEffect, useState } from "react";
import { AdminHeader } from "../../components/admin/AdminHeader";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";
import { StatusDot } from "../../components/common/StatusDot";
import { EmptyState } from "../../components/common/EmptyState";
import { getNetworkStatus } from "../../services/api/client";
import type { NetworkStatus } from "../../types";
import { Radio } from "lucide-react";
import { useAdminOutletContext } from "./AdminLayout";

const REFRESH_MS = 5000;

export function Network() {
  const { onOpenMobileMenu } = useAdminOutletContext();
  const [status, setStatus] = useState<NetworkStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      getNetworkStatus()
        .then((result) => {
          if (!cancelled) {
            setStatus(result);
            setError(null);
          }
        })
        .catch((err: unknown) => {
          if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load network status.");
        });
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const local = status?.connections.filter((c) => c.isLocal) ?? [];
  const external = status?.connections.filter((c) => !c.isLocal) ?? [];
  const flagged = status?.connections.filter((c) => c.flags.length > 0) ?? [];

  return (
    <>
      <AdminHeader title="Network" description="Active connections — LOCAL vs. EXTERNAL" onOpenMobileMenu={onOpenMobileMenu} />
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {error && <p className="mb-4 text-sm text-danger-500">{error}</p>}

        {status && !status.available ? (
          <EmptyState icon={Radio} title="Network monitoring unavailable" description={status.detail} />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Card className="p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">Internal / Local</p>
                <p className="mt-2 text-2xl font-semibold text-neutral-900">{status?.localCount ?? "…"}</p>
              </Card>
              <Card className="p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">External</p>
                <p className="mt-2 text-2xl font-semibold text-neutral-900">{status?.externalCount ?? "…"}</p>
              </Card>
              <Card className="p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">Status</p>
                <p className="mt-2 text-2xl font-semibold text-neutral-900">
                  {status ? (flagged.length === 0 ? "NORMAL" : "REVIEW") : "…"}
                </p>
              </Card>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Internal Connections</CardTitle>
                  <Badge tone="success">LOCAL DATA</Badge>
                </CardHeader>
                <CardContent className="max-h-72 space-y-1.5 overflow-y-auto">
                  {local.length === 0 && <p className="text-sm text-neutral-400">No local connections observed.</p>}
                  {local.map((conn, i) => (
                    <div key={i} className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2 text-xs">
                      <span className="font-mono text-neutral-700">{conn.remoteAddress}</span>
                      <span className="flex items-center gap-1.5 text-neutral-500">
                        <StatusDot tone="success" />
                        {conn.status}
                      </span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>External Connections</CardTitle>
                  <Badge tone="neutral">EXTERNAL</Badge>
                </CardHeader>
                <CardContent className="max-h-72 space-y-1.5 overflow-y-auto">
                  {external.length === 0 && <p className="text-sm text-neutral-400">No external connections observed.</p>}
                  {external.map((conn, i) => (
                    <div key={i} className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2 text-xs">
                      <span className="font-mono text-neutral-700">{conn.remoteAddress}</span>
                      <span className="flex items-center gap-1.5 text-neutral-500">
                        <StatusDot tone={conn.flags.length ? "warning" : "info"} />
                        {conn.status}
                      </span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <Card className="mt-4">
              <CardHeader>
                <CardTitle>Flagged Connections</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {flagged.length === 0 ? (
                  <EmptyState
                    icon={Radio}
                    title="Nothing flagged"
                    description="No connections matched the explainable heuristics in use (uncommon privileged ports, in-progress connection attempts). This is not a security verdict — only a simple, transparent observation."
                  />
                ) : (
                  <ul className="divide-y divide-neutral-100">
                    {flagged.map((conn, i) => (
                      <li key={i} className="px-4 py-3 text-sm text-neutral-700">
                        <span className="font-mono">{conn.remoteAddress}</span> — {conn.flags.join(", ")}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </>
  );
}
