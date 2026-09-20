import { FileAttachmentChip } from "../files/FileAttachmentChip";
import { formatTimestamp } from "../../lib/utils";
import type { ChatMessage } from "../../types";

export function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] space-y-2 sm:max-w-[70%]">
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap justify-end gap-2">
            {message.attachments.map((attachment) => (
              <FileAttachmentChip key={attachment.id} attachment={attachment} />
            ))}
          </div>
        )}
        {message.text && (
          <div className="rounded-2xl rounded-tr-md bg-neutral-900 px-4 py-2.5 text-sm leading-relaxed text-neutral-0">
            {message.text}
          </div>
        )}
        <p className="pr-1 text-right text-xs text-neutral-400">{formatTimestamp(message.createdAt)}</p>
      </div>
    </div>
  );
}
