import { AlertCircle, MoreVertical, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { AdminHeader } from "../../components/admin/AdminHeader";
import { AddModelDialog } from "../../components/admin/AddModelDialog";
import { ModelStatusBadge } from "../../components/admin/ModelStatusBadge";
import { Button } from "../../components/common/Button";
import { Card } from "../../components/common/Card";
import { Dropdown } from "../../components/common/Dropdown";
import { IconButton } from "../../components/common/IconButton";
import { addModel, deleteModel, getModels } from "../../services/api/client";
import type { ModelInfo, NewModelInput } from "../../types";
import { useAdminOutletContext } from "./AdminLayout";

export function Models() {
  const { onOpenMobileMenu } = useAdminOutletContext();
  const [models, setModels] = useState<ModelInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const refresh = () =>
    getModels()
      .then((result) => {
        setModels(result);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load models.");
      });

  useEffect(() => {
    refresh();
  }, []);

  const handleAdd = async (input: NewModelInput) => {
    setSubmitting(true);
    try {
      await addModel(input);
      await refresh();
      setDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add model.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (model: ModelInfo) => {
    setRemovingId(model.id);
    try {
      await deleteModel(model.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove model.");
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <>
      <AdminHeader title="Models" description="Manage local models available to the router" onOpenMobileMenu={onOpenMobileMenu} />
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          {error ? (
            <p className="flex items-center gap-1.5 text-sm text-danger-500">
              <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
              {error}
            </p>
          ) : (
            <span />
          )}
          <Button variant="primary" onClick={() => setDialogOpen(true)}>
            <Plus className="size-4" aria-hidden="true" />
            Add Model
          </Button>
        </div>

        <Card className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-neutral-150 text-neutral-400">
              <tr>
                <th className="px-4 py-2.5 font-medium">Model Name</th>
                <th className="px-4 py-2.5 font-medium">Type</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium">Context</th>
                <th className="px-4 py-2.5 font-medium">Resource Requirement</th>
                <th className="px-4 py-2.5 font-medium">Version</th>
                <th className="px-4 py-2.5 font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {models?.map((model) => (
                <tr key={model.id}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-neutral-900">{model.name}</p>
                    <p className="text-xs text-neutral-400">{model.identifier}</p>
                  </td>
                  <td className="px-4 py-3 capitalize text-neutral-600">{model.type}</td>
                  <td className="px-4 py-3">
                    <ModelStatusBadge status={model.status} />
                  </td>
                  <td className="px-4 py-3 text-neutral-600">{model.contextLength.toLocaleString()} tok</td>
                  <td className="px-4 py-3 text-neutral-600">{model.resourceRequirement}</td>
                  <td className="px-4 py-3 text-neutral-600">{model.version}</td>
                  <td className="px-4 py-3 text-right">
                    <Dropdown
                      align="end"
                      trigger={
                        <IconButton label="Model actions" size="sm" disabled={removingId === model.id}>
                          <MoreVertical className="size-4" />
                        </IconButton>
                      }
                      items={[
                        {
                          id: "remove",
                          label: "Remove",
                          icon: <Trash2 className="size-4" />,
                          destructive: true,
                          onSelect: () => handleRemove(model),
                        },
                      ]}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <AddModelDialog open={dialogOpen} onClose={() => setDialogOpen(false)} onSubmit={handleAdd} submitting={submitting} />
    </>
  );
}
