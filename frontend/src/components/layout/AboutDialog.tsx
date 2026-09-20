import { ShieldHalf } from "lucide-react";
import { Dialog } from "../common/Dialog";
import { Badge } from "../common/Badge";

export function AboutDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onClose={onClose} title="Help & About" size="sm">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-md bg-neutral-900">
            <ShieldHalf className="size-5 text-neutral-0" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold text-neutral-900">Sovereign AI Workbench</p>
            <p className="text-xs text-neutral-400">Version 0.1.0 · Development build</p>
          </div>
        </div>
        <p className="text-sm text-neutral-600">
          A self-hosted AI workbench for confidential work — every conversation, document, and
          model runs on infrastructure your organization controls.
        </p>
        <div className="flex flex-wrap gap-1.5">
          <Badge tone="neutral">Frontend-only build</Badge>
          <Badge tone="neutral">No cloud services</Badge>
        </div>
        <p className="text-xs text-neutral-400">
          Local model inference, retrieval, and agent orchestration will be connected in a later
          release.
        </p>
      </div>
    </Dialog>
  );
}
