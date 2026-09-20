import { AlertCircle, Download, Eye, Loader2 } from "lucide-react";
import { useState } from "react";
import { Button } from "../common/Button";
import { formatBytes } from "../../lib/utils";
import { getFileIcon } from "../files/fileIcon";
import { downloadDeliverable } from "../../services/api/client";
import type { Deliverable } from "../../types";

export function DeliverableCard({ deliverable }: { deliverable: Deliverable }) {
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const Icon = getFileIcon(deliverable.filename);

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(null);
    try {
      const blob = await downloadDeliverable(deliverable.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = deliverable.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="max-w-sm rounded-lg border border-neutral-150 bg-neutral-0 p-3.5 shadow-xs">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-400">
        Generated Deliverable
      </p>
      <div className="flex items-center gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-neutral-100">
          <Icon className="size-5 text-neutral-600" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-neutral-900">{deliverable.filename}</p>
          <p className="truncate text-xs text-neutral-400">
            {deliverable.fileType} · {formatBytes(deliverable.sizeBytes)}
          </p>
        </div>
      </div>

      {deliverable.status === "generating" && (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-neutral-500">
          <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
          Generating…
        </p>
      )}

      {deliverable.status === "failed" && (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-danger-500">
          <AlertCircle className="size-3.5" aria-hidden="true" />
          Generation failed
        </p>
      )}

      {deliverable.status === "ready" && (
        <>
          <div className="mt-3 flex gap-2">
            <Button size="sm" variant="primary" className="flex-1" onClick={handleDownload} loading={downloading}>
              <Download className="size-3.5" aria-hidden="true" />
              Download
            </Button>
            <Button size="sm" variant="secondary">
              <Eye className="size-3.5" aria-hidden="true" />
              Preview
            </Button>
          </div>
          {downloadError && <p className="mt-2 text-xs text-danger-500">{downloadError}</p>}
        </>
      )}
    </div>
  );
}
