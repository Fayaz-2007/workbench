import { AdminHeader } from "../../components/admin/AdminHeader";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/common/Card";
import { Input, Label } from "../../components/common/Input";
import { Switch } from "../../components/common/Switch";
import { Badge } from "../../components/common/Badge";
import { useLocalStorage } from "../../hooks/useLocalStorage";
import { useAdminOutletContext } from "./AdminLayout";

export function Settings() {
  const { onOpenMobileMenu } = useAdminOutletContext();
  const [orgName, setOrgName] = useLocalStorage("admin.orgName", "");
  const [allowUploads, setAllowUploads] = useLocalStorage("admin.allowUploads", true);
  const [requireApproval, setRequireApproval] = useLocalStorage("admin.requireApproval", false);

  return (
    <>
      <AdminHeader title="Settings" description="Workbench-wide configuration" onOpenMobileMenu={onOpenMobileMenu} />
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="mx-auto max-w-2xl space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Organization</CardTitle>
            </CardHeader>
            <CardContent>
              <Label htmlFor="org-name">Organization name</Label>
              <Input
                id="org-name"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="e.g. Refinery Operations Division"
                className="max-w-sm"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Workspace Policy</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-neutral-800">Allow file uploads</p>
                  <p className="text-sm text-neutral-500">Users can attach files to conversations.</p>
                </div>
                <Switch checked={allowUploads} onChange={setAllowUploads} label="Allow file uploads" />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-neutral-800">Require approval for new models</p>
                  <p className="text-sm text-neutral-500">Newly added models start disabled until approved.</p>
                </div>
                <Switch checked={requireApproval} onChange={setRequireApproval} label="Require approval for new models" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Identity Provider</CardTitle>
              <Badge tone="neutral">Not configured</Badge>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-neutral-500">
                SSO and directory sync will appear here once this workbench is connected to your
                organization's identity provider.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
