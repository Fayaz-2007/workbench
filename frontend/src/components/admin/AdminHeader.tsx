import { Menu } from "lucide-react";
import { IconButton } from "../common/IconButton";
import { Badge } from "../common/Badge";

export function AdminHeader({
  title,
  description,
  onOpenMobileMenu,
}: {
  title: string;
  description?: string;
  onOpenMobileMenu: () => void;
}) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-neutral-150 px-4 md:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <IconButton label="Open menu" onClick={onOpenMobileMenu} className="md:hidden">
          <Menu className="size-4" />
        </IconButton>
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold text-neutral-900">{title}</h1>
          {description && <p className="truncate text-xs text-neutral-400">{description}</p>}
        </div>
      </div>
      <Badge tone="neutral">Development Mode</Badge>
    </header>
  );
}
