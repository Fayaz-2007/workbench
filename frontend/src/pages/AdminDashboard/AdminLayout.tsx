import { useState } from "react";
import { Outlet, useOutletContext } from "react-router-dom";
import { AdminSidebar } from "../../components/admin/AdminSidebar";

interface AdminOutletContext {
  onOpenMobileMenu: () => void;
}

export function useAdminOutletContext() {
  return useOutletContext<AdminOutletContext>();
}

export function AdminLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-neutral-0">
      <AdminSidebar mobileOpen={mobileOpen} onCloseMobile={() => setMobileOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Outlet context={{ onOpenMobileMenu: () => setMobileOpen(true) } satisfies AdminOutletContext} />
      </div>
    </div>
  );
}
