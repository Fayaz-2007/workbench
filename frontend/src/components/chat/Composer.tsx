import { ArrowUp, Paperclip } from "lucide-react";
import { useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { IconButton } from "../common/IconButton";
import { FileAttachmentChip } from "../files/FileAttachmentChip";
import { ACCEPTED_FILE_EXTENSIONS } from "../../lib/config";
import { getAgentDisplay } from "../../services/mock/agents";
import type { AgentSelection, ChatAttachment } from "../../types";
import { cn } from "../../lib/utils";

export function Composer({
  agentId,
  attachments,
  isSending,
  onAddFiles,
  onRemoveAttachment,
  onSend,
}: {
  agentId: AgentSelection;
  attachments: ChatAttachment[];
  isSending: boolean;
  onAddFiles: (files: FileList) => void;
  onRemoveAttachment: (id: string) => void;
  onSend: (text: string) => void;
}) {
  const [text, setText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const agent = getAgentDisplay(agentId);

  const hasUploadingAttachment = attachments.some((a) => a.status === "uploading");
  const canSend = (text.trim().length > 0 || attachments.length > 0) && !isSending && !hasUploadingAttachment;

  const resize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const handleSend = () => {
    if (!canSend) return;
    onSend(text.trim());
    setText("");
    requestAnimationFrame(resize);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-neutral-150 bg-neutral-25 px-3 pb-4 pt-3 md:px-6">
      <div className="mx-auto max-w-3xl">
        <div className="rounded-xl border border-neutral-200 bg-neutral-0 shadow-sm focus-within:border-accent-400 focus-within:ring-2 focus-within:ring-accent-100">
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 border-b border-neutral-100 px-3 pt-3">
              {attachments.map((attachment) => (
                <FileAttachmentChip
                  key={attachment.id}
                  attachment={attachment}
                  onRemove={() => onRemoveAttachment(attachment.id)}
                />
              ))}
            </div>
          )}

          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              resize();
            }}
            onKeyDown={handleKeyDown}
            placeholder={agentId === "auto" ? "Describe your task…" : `Message ${agent?.name ?? "the workbench"}…`}
            rows={1}
            aria-label="Message"
            className="max-h-[200px] w-full resize-none bg-transparent px-3.5 pb-1 pt-3 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
          />

          <div className="flex items-center justify-between px-2.5 pb-2.5 pt-1">
            <div className="flex items-center gap-1.5">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept={ACCEPTED_FILE_EXTENSIONS.join(",")}
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.length) onAddFiles(e.target.files);
                  e.target.value = "";
                }}
              />
              <IconButton label="Attach files" onClick={() => fileInputRef.current?.click()} size="sm">
                <Paperclip className="size-4" />
              </IconButton>
              {agent && (
                <span className="hidden items-center gap-1.5 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-600 sm:inline-flex">
                  <agent.icon className="size-3.5" aria-hidden="true" />
                  {agent.name}
                </span>
              )}
            </div>

            <button
              onClick={handleSend}
              disabled={!canSend}
              aria-label="Send message"
              className={cn(
                "flex size-8 items-center justify-center rounded-full transition-colors",
                canSend
                  ? "bg-neutral-900 text-neutral-0 hover:bg-neutral-800"
                  : "bg-neutral-150 text-neutral-400",
              )}
            >
              <ArrowUp className="size-4" aria-hidden="true" />
            </button>
          </div>
        </div>
        <p className="mt-2 text-center text-xs text-neutral-400">
          Runs entirely on your local server. Verify important outputs.
        </p>
      </div>
    </div>
  );
}
