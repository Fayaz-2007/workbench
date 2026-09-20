import { useState } from "react";
import { Dialog } from "../common/Dialog";
import { Button } from "../common/Button";
import { Input, Label, Select } from "../common/Input";
import type { NewModelInput } from "../../types";

const MODEL_TYPES: NewModelInput["type"][] = ["general", "code", "vision", "data", "embedding"];
const STATUSES: NewModelInput["status"][] = ["active", "idle", "loading", "disabled"];

const EMPTY_FORM: NewModelInput = {
  name: "",
  type: "general",
  identifier: "",
  capabilities: "",
  contextLength: 8192,
  quantization: "Q4_K_M",
  status: "disabled",
};

export function AddModelDialog({
  open,
  onClose,
  onSubmit,
  submitting,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (input: NewModelInput) => void;
  submitting: boolean;
}) {
  const [form, setForm] = useState<NewModelInput>(EMPTY_FORM);

  const update = <K extends keyof NewModelInput>(key: K, value: NewModelInput[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = () => {
    if (!form.name.trim() || !form.identifier.trim()) return;
    onSubmit(form);
    setForm(EMPTY_FORM);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Add Model"
      description="Register a model for the router to manage. Downloading and installation happen in a later release."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={submitting}>
            Add Model
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <Label htmlFor="model-name">Model name</Label>
          <Input
            id="model-name"
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            placeholder="e.g. Coding Model"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="model-type">Model type</Label>
            <Select id="model-type" value={form.type} onChange={(e) => update("type", e.target.value as NewModelInput["type"])}>
              {MODEL_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="model-status">Initial status</Label>
            <Select id="model-status" value={form.status} onChange={(e) => update("status", e.target.value as NewModelInput["status"])}>
              {STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div>
          <Label htmlFor="model-identifier">Model identifier</Label>
          <Input
            id="model-identifier"
            value={form.identifier}
            onChange={(e) => update("identifier", e.target.value)}
            placeholder="e.g. qwen2.5-coder-7b"
          />
        </div>

        <div>
          <Label htmlFor="model-capabilities">Capabilities</Label>
          <Input
            id="model-capabilities"
            value={form.capabilities}
            onChange={(e) => update("capabilities", e.target.value)}
            placeholder="e.g. code completion, refactoring"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="model-context">Context length</Label>
            <Input
              id="model-context"
              type="number"
              min={0}
              value={form.contextLength}
              onChange={(e) => update("contextLength", Number(e.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="model-quant">Quantization</Label>
            <Input
              id="model-quant"
              value={form.quantization}
              onChange={(e) => update("quantization", e.target.value)}
              placeholder="e.g. Q4_K_M"
            />
          </div>
        </div>
      </div>
    </Dialog>
  );
}
