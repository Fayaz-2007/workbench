import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <div className="flex size-11 items-center justify-center rounded-lg bg-neutral-100">
        <Icon className="size-5 text-neutral-500" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-neutral-800">{title}</p>
        {description && <p className="max-w-sm text-sm text-neutral-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}
