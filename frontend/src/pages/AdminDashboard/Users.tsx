import { Badge } from "../../components/common/Badge";
import { Card } from "../../components/common/Card";
import { AdminHeader } from "../../components/admin/AdminHeader";
import { useAdminOutletContext } from "./AdminLayout";

const DEV_USERS = [
  { id: "u1", name: "Workbench User", email: "user@site.local", role: "Admin", status: "Active" },
  { id: "u2", name: "Dev Account", email: "dev@site.local", role: "Member", status: "Active" },
];

export function Users() {
  const { onOpenMobileMenu } = useAdminOutletContext();

  return (
    <>
      <AdminHeader title="Users" description="Manage who can access this workbench" onOpenMobileMenu={onOpenMobileMenu} />
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <Badge tone="neutral" className="mb-4">
          Development data · authentication not yet connected
        </Badge>

        <Card className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead className="border-b border-neutral-150 text-neutral-400">
              <tr>
                <th className="px-4 py-2.5 font-medium">Name</th>
                <th className="px-4 py-2.5 font-medium">Email</th>
                <th className="px-4 py-2.5 font-medium">Role</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {DEV_USERS.map((user) => (
                <tr key={user.id}>
                  <td className="px-4 py-3 font-medium text-neutral-900">{user.name}</td>
                  <td className="px-4 py-3 text-neutral-600">{user.email}</td>
                  <td className="px-4 py-3 text-neutral-600">{user.role}</td>
                  <td className="px-4 py-3">
                    <Badge tone="success">{user.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </>
  );
}
