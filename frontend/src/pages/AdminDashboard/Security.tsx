import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { AdminHeader } from "../../components/admin/AdminHeader";
import { Card } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";
import { getSecurityStatus } from "../../services/api/client";
import type { SecurityStatus } from "../../types";
import { useAdminOutletContext } from "./AdminLayout";

export function Security() {
  const { onOpenMobileMenu } = useAdminOutletContext();
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSecurityStatus()
      .then((result) => {
        setStatus(result);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load security status."));
  }, []);

  return (
    <>
      <AdminHeader title="Security" description="Data sovereignty and security status" onOpenMobileMenu={onOpenMobileMenu} />
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {error && <p className="mb-4 text-sm text-danger-500">{error}</p>}

        <Card className="mb-4 p-4">
          <div className="flex items-start gap-3">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-success-50">
              <ShieldCheck className="size-5 text-success-600" aria-hidden="true" />
            </div>
            <p className="text-sm text-neutral-700">
              {status?.summary ?? "Loading sovereignty status…"}
            </p>
          </div>
        </Card>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {(status?.items ?? []).map((item) => (
            <Card key={item.label} className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">{item.label}</p>
              <div className="mt-1.5">
                <Badge tone={item.value.includes("NOT") || item.value.includes("UNAVAILABLE") ? "neutral" : "success"}>
                  {item.value}
                </Badge>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-neutral-500">{item.detail}</p>
            </Card>
          ))}
        </div>
      </div>
    </>
  );
}
