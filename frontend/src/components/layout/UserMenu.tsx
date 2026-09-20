import { cn } from "../../lib/utils";

/**
 * Development placeholder for the signed-in user. Real authentication is
 * out of scope for this segment — this reads from a static dev profile so
 * the identity slot can later be wired to a real session.
 */
const DEV_USER = {
  name: "Workbench User",
  email: "user@site.local",
  initials: "WU",
};

export function UserMenu({ collapsed }: { collapsed: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md px-2 py-1.5",
        collapsed && "justify-center px-0",
      )}
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent-100 text-xs font-semibold text-accent-700">
        {DEV_USER.initials}
      </div>
      {!collapsed && (
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-neutral-800">{DEV_USER.name}</p>
          <p className="truncate text-xs text-neutral-400">{DEV_USER.email}</p>
        </div>
      )}
    </div>
  );
}
