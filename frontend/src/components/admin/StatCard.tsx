import type { LucideIcon } from "lucide-react";
import { Card } from "../common/Card";

export function StatCard({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 text-neutral-500">
        <Icon className="size-4" aria-hidden="true" />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-semibold text-neutral-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-neutral-400">{hint}</p>}
    </Card>
  );
}
