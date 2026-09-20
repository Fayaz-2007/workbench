import { AlertCircle, Loader2, X } from "lucide-react";
import { formatBytes } from "../../lib/utils";
import { getFileIcon } from "./fileIcon";
import type { ChatAttachment } from "../../types";

export function FileAttachmentChip({
  attachment,
  onRemove,
}: {
  attachment: ChatAttachment;
  onRemove?: () => void;
}) {
  const Icon = getFileIcon(attachment.filename);
  const isError = attachment.status === "error";
  const isUploading = attachment.status === "uploading";

  return (
    <div className="group flex items-center gap-2.5 rounded-md border border-neutral-150 bg-neutral-0 py-1.5 pl-2.5 pr-2 shadow-xs">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-neutral-100">
        {isUploading ? (
          <Loader2 className="size-4 animate-spin text-neutral-500" aria-hidden="true" />
        ) : isError ? (
          <AlertCircle className="size-4 text-danger-500" aria-hidden="true" />
        ) : (
          <Icon className="size-4 text-neutral-600" aria-hidden="true" />
        )}
      </div>

      <div className="min-w-0 max-w-[180px]">
        <p className="truncate text-sm font-medium text-neutral-800">{attachment.filename}</p>
        {isError ? (
          <p className="truncate text-xs text-danger-500">{attachment.errorMessage ?? "Upload failed"}</p>
        ) : isUploading ? (
          <p className="truncate text-xs text-neutral-400">Uploading… {attachment.progress ?? 0}%</p>
        ) : (
          <p className="truncate text-xs text-neutral-400">
            {attachment.fileType} · {formatBytes(attachment.sizeBytes)}
          </p>
        )}
      </div>

      {onRemove && (
        <button
          onClick={onRemove}
          aria-label={`Remove ${attachment.filename}`}
          className="ml-1 flex size-6 shrink-0 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
        >
          <X className="size-3.5" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
