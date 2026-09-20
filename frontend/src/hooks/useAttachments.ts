import { useCallback, useState } from "react";
import { uploadFile } from "../services/api/client";
import { config, ACCEPTED_FILE_EXTENSIONS } from "../lib/config";
import { formatBytes, generateId, getFileTypeLabel } from "../lib/utils";
import type { ChatAttachment } from "../types";

const MAX_BYTES = config.maxUploadMb * 1024 * 1024;

export function useAttachments() {
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);

  const addFiles = useCallback((files: FileList | File[]) => {
    for (const file of Array.from(files)) {
      const ext = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
      const id = generateId("att");

      if (!ACCEPTED_FILE_EXTENSIONS.includes(ext)) {
        setAttachments((prev) => [
          ...prev,
          {
            id,
            filename: file.name,
            fileType: getFileTypeLabel(file.name),
            sizeBytes: file.size,
            status: "error",
            errorMessage: "Unsupported file type",
          },
        ]);
        continue;
      }

      if (file.size > MAX_BYTES) {
        setAttachments((prev) => [
          ...prev,
          {
            id,
            filename: file.name,
            fileType: getFileTypeLabel(file.name),
            sizeBytes: file.size,
            status: "error",
            errorMessage: `Exceeds ${formatBytes(MAX_BYTES)} limit`,
          },
        ]);
        continue;
      }

      setAttachments((prev) => [
        ...prev,
        {
          id,
          filename: file.name,
          fileType: getFileTypeLabel(file.name),
          sizeBytes: file.size,
          status: "uploading",
          progress: 0,
        },
      ]);

      uploadFile(file, {
        onProgress: (progress) => {
          setAttachments((prev) =>
            prev.map((a) => (a.id === id ? { ...a, progress } : a)),
          );
        },
      })
        .then((result) => {
          setAttachments((prev) =>
            prev.map((a) => (a.id === id ? { ...result, id } : a)),
          );
        })
        .catch((error: unknown) => {
          setAttachments((prev) =>
            prev.map((a) =>
              a.id === id
                ? {
                    ...a,
                    status: "error",
                    errorMessage: error instanceof Error ? error.message : "Upload failed",
                  }
                : a,
            ),
          );
        });
    }
  }, []);

  const removeAttachment = useCallback((id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const clearAttachments = useCallback(() => setAttachments([]), []);

  return { attachments, addFiles, removeAttachment, clearAttachments };
}
