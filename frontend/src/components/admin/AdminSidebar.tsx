import {
  Activity,
  ArrowLeft,
  ClipboardList,
  Cpu,
  LayoutDashboard,
  Network,
  Settings,
  ShieldCheck,
  ShieldHalf,
  Users,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "../../lib/utils";
import { UserMenu } from "../layout/UserMenu";
import { IconButton } from "../common/IconButton";

const NAV_ITEMS: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: "/admin", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/admin/models", label: "Models", icon: Cpu },
  { to: "/admin/users", label: "Users", icon: Users },
  { to: "/admin/system", label: "System", icon: Activity },
  { to: "/admin/network", label: "Network", icon: Network },
  { to: "/admin/security", label: "Security", icon: ShieldCheck },
  { to: "/admin/audit-logs", label: "Audit Logs", icon: ClipboardList },
  { to: "/admin/settings", label: "Settings", icon: Settings },
];

export function AdminSidebar({
  mobileOpen,
  onCloseMobile,
}: {
  mobileOpen: boolean;
  onCloseMobile: () => void;
}) {
  const content = (
    <div className="flex h-full flex-col bg-neutral-25">
      <div className="flex h-14 shrink-0 items-center justify-between gap-2 px-3">
        <div className="flex items-center gap-2">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-neutral-900">
            <ShieldHalf className="size-4.5 text-neutral-0" aria-hidden="true" />
          </div>
          <span className="text-[15px] font-semibold leading-tight text-neutral-900">
            Admin
            <span className="block text-[11px] font-medium text-neutral-500">Sovereign AI Workbench</span>
          </span>
        </div>
        <IconButton label="Close menu" onClick={onCloseMobile} className="md:hidden">
          <X className="size-4" />
        </IconButton>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onCloseMobile}
            className={({ isActive }) =>
              cn(
                "flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors",
                isActive
                  ? "bg-neutral-150 font-medium text-neutral-900"
                  : "text-neutral-600 hover:bg-neutral-100",
              )
            }
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="shrink-0 space-y-1 border-t border-neutral-150 px-3 py-3">
        <UserMenu collapsed={false} />
        <NavLink
          to="/"
          className="flex h-9 w-full items-center gap-2 rounded-md px-2 text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        >
          <ArrowLeft className="size-4 shrink-0" aria-hidden="true" />
          Back to Workbench
        </NavLink>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden w-64 shrink-0 border-r border-neutral-150 md:block">{content}</aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-neutral-950/40" onClick={onCloseMobile} aria-hidden="true" />
          <aside className="relative z-10 h-full w-72 max-w-[85vw] border-r border-neutral-150 bg-neutral-25 shadow-lg">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
