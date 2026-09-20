import { Wrench } from "lucide-react";
import type { ChatMessage } from "../../types";

export function ToolMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex items-center gap-2 pl-10 text-xs text-neutral-500">
      <Wrench className="size-3.5" aria-hidden="true" />
      <span>
        Ran tool <span className="font-medium text-neutral-700">{message.toolName}</span>
      </span>
    </div>
  );
}
